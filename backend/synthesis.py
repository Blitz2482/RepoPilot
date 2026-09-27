from __future__ import annotations

import asyncio
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from bob_client import generate_narration
from config import settings
from models import AgentFinding, ArchitectureSummary, OnboardingPlan, RepoContext, TourStep


def _evidence_score(item: dict) -> float:
    path = item.get("path", "").lower()
    score = 0.0
    filename = Path(path).name
    if any(token in filename for token in ("main", "index", "server", "app", "cli")):
        score += 10
    if any(token in path for token in ("src/", "lib/", "core/", "app/")):
        score += 4
    if filename.startswith("readme"):
        score += 2
    score += max(0.0, 2.0 - (item.get("start", 1) / 10000))
    return score


def _candidate_from_parsed(parsed: dict) -> dict:
    symbols = parsed.get("symbols", [])
    if symbols:
        preferred_types = {
            "function_definition", "class_definition", "function_declaration",
            "class_declaration", "method_definition", "arrow_function",
        }
        preferred_names = {"main", "app", "server", "start", "run", "init", "cli"}

        def rank(symbol: dict) -> tuple[int, int, int]:
            symbol_type = str(symbol.get("type", ""))
            name = str(symbol.get("name", "")).lower()
            semantic = 0 if symbol_type in preferred_types else 1
            entry = 0 if name in preferred_names else 1
            return (semantic, entry, int(symbol.get("start_line", 1)))

        symbol = sorted(symbols, key=rank)[0]
        return {
            "path": parsed["path"],
            "start": symbol["start_line"],
            "end": min(symbol["end_line"], symbol["start_line"] + 120),
            "note": f"Symbol {symbol['name']} provides a concrete learning anchor",
        }
    return {
        "path": parsed["path"],
        "start": 1,
        "end": min(30, max(1, parsed.get("content", "").count("\n") + 1)),
        "note": "Repository file provides a concrete fallback onboarding anchor",
    }


def _source_bounds(repo_path: str) -> dict[str, int]:
    """Return safe line counts for files the frontend is allowed to display."""
    from ingest import list_displayable_files

    base = Path(repo_path)
    bounds: dict[str, int] = {}
    for rel in list_displayable_files(repo_path):
        target = (base / rel).resolve()
        try:
            if base.resolve() not in target.parents or not target.is_file() or target.is_symlink():
                continue
            content = target.read_text(encoding="utf-8", errors="replace")
        except (OSError, UnicodeError):
            continue
        bounds[rel] = max(1, len(content.splitlines()))
    return bounds


MAX_TOUR_LINES = 120


def _normalize_evidence(item: dict, bounds: dict[str, int]) -> dict | None:
    path = str(item.get("path", "")).replace("\\", "/").lstrip("/")
    if path not in bounds:
        return None
    try:
        start = max(1, int(item.get("start", 1)))
        end = max(start, int(item.get("end", start)))
    except (TypeError, ValueError):
        return None
    start = min(start, bounds[path])
    end = min(max(start, end), start + MAX_TOUR_LINES - 1, bounds[path])
    return {
        "path": path,
        "start": start,
        "end": end,
        "note": str(item.get("note", ""))[:1000],
    }


def _normalize_narration(text: str, item: dict) -> str:
    cleaned = " ".join(str(text).replace("\n", " ").split())
    if not cleaned:
        return _fallback_narration(item)
    # Keep the tour readable and bounded: take at most two sentence-like units.
    import re
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip()]
    if len(parts) >= 2:
        return f"{parts[0]} {parts[1]}"
    if len(parts) == 1:
        path = item.get("path", "this file")
        return f"{parts[0]} The cited range in {path} is the evidence boundary for this onboarding step."
    return _fallback_narration(item)


def _fallback_narration(item: dict) -> str:
    path = item.get("path", "this file")
    start = item.get("start", 1)
    end = item.get("end", start)
    return (
        f"This onboarding step uses {path} lines {start}-{end} as a concrete repository anchor. "
        "The explanation is limited to behavior visible in that cited source range and does not assume missing context."
    )


async def _narrate_with_fallback(item: dict) -> str:
    try:
        # Keep each narration call bounded so the eight-step synthesis can finish
        # within the enclosing 120-second graph-node budget in normal operation.
        generated = await asyncio.wait_for(generate_narration(item), timeout=min(30, settings.node_timeout_seconds))
        return _normalize_narration(generated, item)
    except Exception:
        return _fallback_narration(item)


async def generate_tour(findings: list[AgentFinding | dict], parsed_files: list[dict] | None = None, repo_path: str | None = None) -> list[dict]:
    evidence: list[dict] = []
    for finding in findings:
        data = finding.model_dump() if isinstance(finding, AgentFinding) else finding
        evidence.extend([e.model_dump() if hasattr(e, "model_dump") else e for e in data.get("evidence", [])])

    bounds = _source_bounds(repo_path) if repo_path else {}
    normalized: list[dict] = []
    for item in sorted(evidence, key=_evidence_score, reverse=True):
        if bounds:
            item = _normalize_evidence(item, bounds)
        if item:
            normalized.append(item)

    unique: list[dict] = []
    seen: set[tuple] = set()
    for item in normalized:
        key = (item.get("path"), int(item.get("start", 1)), int(item.get("end", 1)))
        if key not in seen and key[0]:
            seen.add(key)
            unique.append(item)

    # Add deterministic repository-derived anchors, including README-derived
    # entries, rather than relying only on agent output.
    if repo_path and bounds:
        for readme_name in ("README.md", "README.MD", "README.mdx", "README.rst", "README.txt"):
            if readme_name in bounds:
                candidate = {
                    "path": readme_name,
                    "start": 1,
                    "end": min(30, bounds[readme_name]),
                    "note": "README-derived onboarding context",
                }
                key = (candidate["path"], candidate["start"], candidate["end"])
                if key not in seen:
                    unique.append(candidate)
                    seen.add(key)
                break

    if parsed_files and bounds:
        parsed_candidates = sorted(
            parsed_files,
            key=lambda p: _evidence_score({"path": p.get("path", ""), "start": 1}),
            reverse=True,
        )
        for parsed in parsed_candidates:
            candidate = _candidate_from_parsed(parsed)
            candidate = _normalize_evidence(candidate, bounds)
            if not candidate:
                continue
            key = (candidate["path"], candidate["start"], candidate["end"])
            if key not in seen:
                unique.append(candidate)
                seen.add(key)
            if len(unique) >= 8:
                break

    # A code tour must point at a real source range. If the repository contains
    # no supported displayable source, fail explicitly rather than generating
    # fabricated citations that the source endpoint cannot serve.
    if not unique:
        raise ValueError("Repository contains no supported source files for the code tour")

    fallback_index = 1
    while len(unique) < 8:
        base = unique[(fallback_index - 1) % len(unique)]
        clone = dict(base)
        clone["note"] = (
            f"Fallback onboarding anchor {fallback_index}; source evidence remains the same concrete repository range"
        )
        unique.append(clone)
        fallback_index += 1

    # Bob narrations can run concurrently, while a semaphore prevents an eight-
    # request burst from overwhelming the provider. The order is preserved.
    semaphore = asyncio.Semaphore(4)

    async def bounded(item: dict) -> str:
        async with semaphore:
            return await _narrate_with_fallback(item)

    narrations = await asyncio.gather(*(bounded(item) for item in unique[:8]))
    return [
        {
            "step": idx,
            "title": f"Step {idx}: {Path(item['path']).name}",
            "path": item["path"],
            "start": int(item["start"]),
            "end": int(item["end"]),
            "narration": narrations[idx - 1],
        }
        for idx, item in enumerate(unique[:8], 1)
    ]


def build_learning_path(findings: list[AgentFinding | dict], role: str) -> list[str]:
    concepts: list[str] = []
    role_defaults = {
        "Backend": ["API contracts", "database layer", "request lifecycle"],
        "Frontend": ["component tree", "state management", "data fetching"],
        "Full-Stack": ["API contracts", "component/data flow", "persistence boundary"],
        "Data": ["data models", "transformation pipeline", "storage boundary"],
        "DevOps": ["service startup", "deployment configuration", "observability"],
        "QA": ["entry points", "core flows", "error handling"],
    }
    concepts.extend(role_defaults.get(role, role_defaults["Full-Stack"]))
    for finding in findings:
        data = finding.model_dump() if isinstance(finding, AgentFinding) else finding
        summary = str(data.get("summary", ""))
        if summary and summary != "insufficient evidence":
            concepts.append(summary.split(".")[0][:100])
        for evidence in data.get("evidence", [])[:2]:
            note = evidence.note if hasattr(evidence, "note") else evidence.get("note", "")
            if note:
                concepts.append(note[:100])
    return list(dict.fromkeys(concepts))[:8]


async def build_plan(
    findings: list[AgentFinding | dict],
    role: str,
    repo_context: RepoContext,
    parsed_files: list[dict],
    repo_path: str | None = None,
) -> dict:
    arch = next((f for f in findings if (f.agent if isinstance(f, AgentFinding) else f.get("agent")) == "architecture"), None)
    biz = next((f for f in findings if (f.agent if isinstance(f, AgentFinding) else f.get("agent")) == "business_logic"), None)
    arch_data = arch.model_dump() if isinstance(arch, AgentFinding) else (arch or {})
    module_counter = Counter()
    for ev in arch_data.get("evidence", []):
        path = ev.get("path", "")
        if path:
            module_counter[path.split("/")[0]] += 1
    modules = [m for m, _ in module_counter.most_common(5)]
    entry_points = [p["path"] for p in parsed_files if any(token in Path(p["path"]).name.lower() for token in ("main", "index", "server", "app", "cli"))][:5]
    architecture = ArchitectureSummary(
        overview=str(arch_data.get("summary", "insufficient evidence")),
        modules=modules,
        entry_points=entry_points,
        data_flow=str(arch_data.get("summary", "insufficient evidence")),
    )
    steps = await generate_tour(findings, parsed_files, repo_path)
    concepts = build_learning_path([biz or {}, arch or {}], role)
    plan = OnboardingPlan(
        role=role,
        tour_steps=[TourStep(**step) for step in steps],
        architecture_summary=architecture,
        key_concepts=concepts,
        repo_context=repo_context,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    return plan.model_dump()
