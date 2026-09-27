from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from config import settings
from models import AgentFinding, Evidence
from prompts import build_architecture_prompt, build_business_logic_prompt, build_qa_prompt

logger = logging.getLogger(__name__)
BOB_LOG_DIR = Path("/tmp/bob_logs")
BOB_LOG_DIR.mkdir(parents=True, exist_ok=True)
MAX_RETRIES = 2
_RETRYABLE_HTTP = {408, 409, 425, 429}


def _safe_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, default=str)


def _extract_json(raw: Any) -> dict | None:
    if isinstance(raw, dict):
        output = raw.get("output")
        if isinstance(output, dict):
            return output
        if isinstance(output, str):
            raw = output
        elif {"summary", "evidence"}.issubset(raw.keys()) or {"answer", "citations"}.issubset(raw.keys()):
            return raw
    if isinstance(raw, str):
        text = raw.strip()
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
        try:
            parsed = json.loads(text)
            return parsed if isinstance(parsed, dict) else None
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.S)
            if match:
                try:
                    parsed = json.loads(match.group(0))
                    return parsed if isinstance(parsed, dict) else None
                except json.JSONDecodeError:
                    return None
    return None


def _log_exchange(kind: str, payload: Any) -> None:
    if not settings.bob_log_exchanges:
        return
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    # Deliberately disabled by default in production because responses may contain
    # repository-derived content. Evidence capture can be enabled for a controlled demo.
    (BOB_LOG_DIR / f"{stamp}_{kind}.json").write_text(_safe_json(payload), encoding="utf-8")


def _mock_architecture(repo_path: str) -> dict:
    from parser import parse_repo
    parsed = parse_repo(repo_path)
    entry_candidates = [
        f for f in parsed
        if any(token in Path(f["path"]).name.lower() for token in ("main", "index", "server", "app", "cli"))
    ]
    selected = entry_candidates[:5] or parsed[:5]
    evidence = []
    modules = []
    for item in selected:
        symbols = item.get("symbols", [])
        start = symbols[0]["start_line"] if symbols else 1
        end = symbols[-1]["end_line"] if symbols else min(30, max(1, item.get("content", "").count("\n") + 1))
        evidence.append({"path": item["path"], "start": start, "end": end, "note": "Code-bearing module selected from the parsed repository"})
        modules.append(item["path"].split("/")[0])
    modules = list(dict.fromkeys(modules))[:5]
    return {
        "summary": "The mock analysis uses parsed repository structure to identify likely entry-point files and top-level modules. It does not infer behavior beyond the available code evidence.",
        "evidence": evidence,
        "confidence": 0.65,
        "modules": modules,
    }


def _mock_business_logic(repo_path: str) -> dict:
    from parser import parse_repo
    parsed = parse_repo(repo_path)
    selected = [p for p in parsed if p.get("symbols")][:6]
    evidence = []
    concepts = []
    for item in selected[:5]:
        symbol = item["symbols"][0]
        evidence.append({
            "path": item["path"],
            "start": symbol["start_line"],
            "end": min(symbol["end_line"], symbol["start_line"] + 120),
            "note": f"Parsed symbol {symbol['name']} is concrete repository evidence",
        })
        concepts.append(symbol["name"])
    concepts = list(dict.fromkeys(concepts))[:5]
    return {
        "summary": "The mock domain analysis derives candidate concepts from concrete functions/classes/methods. Business semantics are intentionally conservative in demo mode.",
        "evidence": evidence,
        "confidence": 0.55,
        "concepts": concepts,
    }


def _mock_qa(question: str, chunks: list[dict]) -> dict:
    q_terms = {t.lower() for t in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]+", question)}
    best = None
    best_score = 0
    for chunk in chunks:
        terms = {t.lower() for t in re.findall(r"[a-zA-Z_][a-zA-Z0-9_]+", chunk.get("content", ""))}
        score = len(q_terms & terms)
        if score > best_score:
            best, best_score = chunk, score
    if not best:
        return {"answer": "insufficient evidence", "citations": []}
    return {
        "answer": f"The retrieved code most directly related to your question is {best['path']} lines {best['start_line']}-{best['end_line']}. Demo mode only summarizes the supplied evidence.",
        "citations": [{"path": best["path"], "start": best["start_line"], "end": best["end_line"]}],
    }


async def _call_openai(prompt: str, json_mode: bool = True) -> Any:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured")
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=min(settings.node_timeout_seconds, 25), max_retries=0)
    response = await client.chat.completions.create(
        model=settings.openai_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        response_format={"type": "json_object"} if json_mode else None,
        timeout=min(settings.node_timeout_seconds, 25),
    )
    return response.choices[0].message.content or ""


async def _call_bob(prompt: str, repo_path: str | None = None) -> Any:
    if settings.mock_bob:
        if "Architecture Agent" in prompt:
            return _mock_architecture(repo_path or ".")
        if "Business Logic Agent" in prompt:
            return _mock_business_logic(repo_path or ".")
        if "grounded Q&A" in prompt:
            return _mock_qa("", [])

    if not settings.bob_api_key:
        return await _call_openai(prompt, json_mode=True)

    url = settings.bob_base_url.rstrip("/") + "/" + settings.bob_endpoint.lstrip("/")
    payload = {
        "prompt": prompt,
        "repo_path": repo_path,
        "mode": "agent",
        "output_format": "json",
    }
    _log_exchange("request", {"url": url, "payload": {**payload, "prompt_length": len(prompt)}})
    # Keep an individual provider call bounded below the graph-node timeout so
    # one failed agent cannot consume the entire node retry budget.
    provider_timeout = min(settings.node_timeout_seconds, 30)
    timeout = httpx.Timeout(provider_timeout, connect=min(10, provider_timeout))

    last_error: Exception | None = None
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(MAX_RETRIES + 1):
            started = time.perf_counter()
            try:
                response = await client.post(
                    url,
                    headers={"Authorization": f"Bearer {settings.bob_api_key}"},
                    json=payload,
                )
                if response.status_code in _RETRYABLE_HTTP or response.status_code >= 500:
                    if attempt == MAX_RETRIES:
                        response.raise_for_status()
                    await asyncio.sleep(2 ** attempt)
                    continue
                response.raise_for_status()
                raw = response.json()
                _log_exchange("response", {"elapsed_seconds": round(time.perf_counter() - started, 3), "response": raw})
                return raw
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                last_error = exc
                if attempt == MAX_RETRIES:
                    break
                await asyncio.sleep(2 ** attempt)
            except httpx.HTTPStatusError as exc:
                # Do not silently hide configuration/authentication errors.
                last_error = exc
                if exc.response.status_code not in _RETRYABLE_HTTP and exc.response.status_code < 500:
                    raise
                if attempt == MAX_RETRIES:
                    break
                await asyncio.sleep(2 ** attempt)

    if settings.openai_api_key and last_error is not None:
        logger.warning("Bob provider unavailable; using configured fallback: %s", type(last_error).__name__)
        return await _call_openai(prompt, json_mode=True)
    if last_error is not None:
        raise RuntimeError("Bob provider is unavailable") from last_error
    raise RuntimeError("Bob request failed")


async def _parse_with_repair(raw: Any, schema_label: str, original_prompt: str, repo_path: str | None) -> dict:
    parsed = _extract_json(raw)
    if parsed is not None:
        return parsed
    repair_prompt = (
        f"Repair the previous response into strict JSON for schema {schema_label}. "
        "Return JSON only. Preserve only facts present in the original response.\n"
        f"Original prompt:\n{original_prompt}\nOriginal response:\n{_safe_json(raw)}"
    )
    if settings.mock_bob:
        raise ValueError(f"Malformed mock response for {schema_label}")
    repaired = await _call_bob(repair_prompt, repo_path)
    parsed = _extract_json(repaired)
    if parsed is None:
        raise ValueError(f"Bob returned malformed {schema_label} JSON after repair")
    return parsed


def _normalize_finding(data: dict, agent: str) -> AgentFinding:
    evidence = []
    for item in data.get("evidence", []) or []:
        try:
            evidence.append(Evidence(
                path=str(item["path"]),
                start=max(1, int(item["start"])),
                end=max(1, int(item["end"])),
                note=str(item.get("note", "")),
            ))
        except (KeyError, TypeError, ValueError):
            continue
    confidence = float(data.get("confidence", 0.5))
    return AgentFinding(
        agent=agent,
        summary=str(data.get("summary", "insufficient evidence")),
        evidence=evidence,
        confidence=max(0.0, min(1.0, confidence)),
    )


async def analyze_architecture(repo_path: str, languages: list[str] | None = None, file_count: int = 0) -> AgentFinding:
    prompt = build_architecture_prompt(repo_path, languages or [], file_count)
    raw = await _call_bob(prompt, repo_path)
    parsed = await _parse_with_repair(raw, "AgentFinding", prompt, repo_path)
    return _normalize_finding(parsed, "architecture")


async def analyze_business_logic(repo_path: str) -> AgentFinding:
    prompt = build_business_logic_prompt(repo_path)
    raw = await _call_bob(prompt, repo_path)
    parsed = await _parse_with_repair(raw, "AgentFinding", prompt, repo_path)
    return _normalize_finding(parsed, "business_logic")


async def generate_narration(evidence: dict) -> str:
    prompt = (
        "You are narrating a code tour step. Use ONLY this evidence. "
        "Return exactly two clear sentences explaining what the code does and WHY it matters to onboarding. "
        "Do not invent behavior.\n" + _safe_json(evidence)
    )
    if settings.mock_bob:
        path = evidence.get("path", "this file")
        start = evidence.get("start", 1)
        end = evidence.get("end", start)
        return f"Start with {path} lines {start}-{end} because it is a concrete onboarding anchor. The step explains the repository behavior visible in this evidence without relying on assumptions."
    raw = await _call_bob(prompt, None)
    parsed = _extract_json(raw)
    if parsed and isinstance(parsed.get("narration"), str):
        return parsed["narration"]
    return str(raw.get("output", raw) if isinstance(raw, dict) else raw)


async def answer_with_bob(question: str, chunks: list[dict]) -> dict:
    prompt = build_qa_prompt(question, chunks)
    if settings.mock_bob:
        return _mock_qa(question, chunks)
    try:
        raw = await _call_bob(prompt, None)
        parsed = _extract_json(raw)
        if parsed is None:
            text = raw.get("output", raw) if isinstance(raw, dict) else raw
            return {"answer": str(text), "citations": []}
        citations = []
        for c in parsed.get("citations", []) or []:
            try:
                citations.append({"path": str(c["path"]), "start": int(c["start"]), "end": int(c["end"])})
            except (KeyError, TypeError, ValueError):
                pass
        return {"answer": str(parsed.get("answer", "insufficient evidence")), "citations": citations}
    except httpx.TimeoutException:
        raise
    except Exception:
        if settings.openai_api_key:
            raw = await _call_openai(prompt, json_mode=True)
            parsed = _extract_json(raw) or {"answer": str(raw), "citations": []}
            return parsed
        raise
