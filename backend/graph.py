from __future__ import annotations

import asyncio
import time
from typing import TypedDict

try:
    from langgraph.graph import END, StateGraph
except ImportError:  # local fallback; production requirements install LangGraph
    END = "__END__"
    class StateGraph:
        def __init__(self, state_type): self.nodes = []; self.entry = None
        def add_node(self, name, fn): self.nodes.append((name, fn))
        def set_entry_point(self, name): self.entry = name
        def add_edge(self, a, b): pass
        def compile(self):
            nodes = dict(self.nodes); order = [name for name, _ in self.nodes]
            class Compiled:
                async def astream(self, state):
                    current = dict(state)
                    for name in order:
                        current = await nodes[name](current)
                        yield {name: current}
            return Compiled()

from config import settings


class RepoPilotState(TypedDict, total=False):
    job_id: str
    repo_url: str
    role: str
    repo_path: str | None
    repo_context: dict | None
    parsed_files: list
    chunks: list
    findings: list[dict]
    plan: dict | None
    status: str
    error: str | None


async def _run_step(label: str, func, state: RepoPilotState, timeout: int | None = None):
    from job_store import set_progress
    for attempt in range(3):
        try:
            await set_progress(state["job_id"], label, "running", 5, f"{label} started")
            return await asyncio.wait_for(func(), timeout=timeout or settings.node_timeout_seconds)
        except Exception as exc:
            if attempt == 2:
                await set_progress(state["job_id"], label, "failed", 0, f"{label} failed", error=type(exc).__name__)
                raise
            await asyncio.sleep(2 ** attempt)


async def ingest_node(state: RepoPilotState) -> RepoPilotState:
    from ingest import clone_repo, inspect_repository
    path = await _run_step("ingest", lambda: clone_repo(state["repo_url"], state["job_id"]), state)
    context = inspect_repository(path, state["repo_url"])
    from job_store import update_job
    await update_job(state["job_id"], repo_path=path, repo_context=context)
    return {**state, "repo_path": path, "repo_context": context, "status": "ingested", "error": None}


async def parse_node(state: RepoPilotState) -> RepoPilotState:
    from parser import parse_repo
    from ingest import list_displayable_files
    files = await _run_step("parse", lambda: asyncio.to_thread(parse_repo, state["repo_path"]), state)
    from job_store import update_job
    await update_job(state["job_id"], source_paths=list_displayable_files(state["repo_path"]))
    return {**state, "parsed_files": files, "status": "parsed"}


async def embed_node(state: RepoPilotState) -> RepoPilotState:
    from chunker import chunk_parsed_files
    from embedder import embed_chunks
    chunks = chunk_parsed_files(state.get("parsed_files", []))
    await _run_step("embed", lambda: embed_chunks(state["job_id"], chunks), state)
    from job_store import update_job
    await update_job(state["job_id"], chunks=chunks)
    return {**state, "chunks": chunks, "status": "embedded"}


async def _run_agent(job_id: str, name: str, func):
    from job_store import get_job, publish, update_job
    started = time.perf_counter()
    record = get_job(job_id)
    if record:
        record.agents[name] = {"status": "running", "latest_message": f"{name} agent started", "started_at": time.time(), "elapsed_seconds": 0}
    await publish(job_id, {"event": "agent_progress", "node": "fanout", "agent": name, "status": "running", "progress": 55 if name == "Architecture" else 65, "latest_message": f"{name} agent started", "agents": record.agents if record else {}})
    try:
        result = await func()
        elapsed = round(time.perf_counter() - started, 2)
        record = get_job(job_id)
        if record:
            record.agents[name].update({"status": "done", "latest_message": "Completed", "elapsed_seconds": elapsed})
            agents = record.agents
        else:
            agents = {}
        await publish(job_id, {"event": "agent_progress", "node": "fanout", "agent": name, "status": "done", "progress": 70, "latest_message": "Completed", "agents": agents})
        return result
    except Exception as exc:
        elapsed = round(time.perf_counter() - started, 2)
        record = get_job(job_id)
        if record:
            record.agents.setdefault(name, {}).update({"status": "failed", "latest_message": "Agent failed", "elapsed_seconds": elapsed, "error": type(exc).__name__})
            agents = record.agents
        else:
            agents = {}
        await publish(job_id, {"event": "agent_progress", "node": "fanout", "agent": name, "status": "failed", "progress": 70, "latest_message": "Agent failed", "agents": agents})
        raise


async def _fanout_impl(state: RepoPilotState) -> RepoPilotState:
    from bob_client import analyze_architecture, analyze_business_logic
    ctx = state.get("repo_context") or {}
    results = await asyncio.gather(
        _run_agent(state["job_id"], "Architecture", lambda: analyze_architecture(state["repo_path"], ctx.get("languages", []), ctx.get("file_count", 0))),
        _run_agent(state["job_id"], "Business Logic", lambda: analyze_business_logic(state["repo_path"])),
        return_exceptions=True,
    )
    findings = [r.model_dump() for r in results if not isinstance(r, Exception)]
    errors = [f"{type(r).__name__}: {r}" for r in results if isinstance(r, Exception)]
    if not findings:
        raise RuntimeError("Both Bob analysis agents failed")
    return {**state, "findings": findings, "status": "analyzed", "error": "; ".join(errors) if errors else None}


async def fanout_node(state: RepoPilotState) -> RepoPilotState:
    # Fan-out itself is a graph node, so apply the same retry/timeout contract
    # as the other nodes while still allowing partial agent failures.
    return await _run_step("fanout", lambda: _fanout_impl(state), state)


async def synthesize_node(state: RepoPilotState) -> RepoPilotState:
    from models import RepoContext
    from synthesis import build_plan
    context = RepoContext(**state["repo_context"])
    plan = await _run_step("synthesize", lambda: build_plan(state.get("findings", []), state["role"], context, state.get("parsed_files", []), state.get("repo_path")), state)
    return {**state, "plan": plan, "status": "synthesized"}


async def _emit_impl(state: RepoPilotState) -> RepoPilotState:
    from db import save_plan
    from job_store import get_job, update_job, publish

    # The emit stage is also retried by _run_step. PostgreSQL writes are idempotent
    # for a repository because save_plan replaces the prior plan for the job.
    if settings.database_url and state.get("plan"):
        await asyncio.to_thread(save_plan, state["job_id"], state["plan"])

    record = await update_job(
        state["job_id"],
        status="done",
        progress=100,
        latest_message="Onboarding plan ready",
        plan=state.get("plan"),
        repo_path=state.get("repo_path"),
        error=state.get("error"),
    )
    now = time.time()
    for agent in ("Architecture", "Business Logic"):
        record.agents.setdefault(agent, {})
        started = record.agents[agent].get("started_at", now)
        if record.agents[agent].get("status") != "failed":
            record.agents[agent].update({
                "status": "done",
                "latest_message": "Completed",
                "elapsed_seconds": round(now - started, 1),
            })
    await publish(
        state["job_id"],
        {
            "event": "complete",
            "job_id": state["job_id"],
            "progress": 100,
            "agents": record.agents,
            "degraded": bool(state.get("error")),
        },
    )
    return state


async def emit_node(state: RepoPilotState) -> RepoPilotState:
    return await _run_step("emit", lambda: _emit_impl(state), state)


def build_graph():
    graph = StateGraph(RepoPilotState)
    graph.add_node("ingest", ingest_node)
    graph.add_node("parse", parse_node)
    graph.add_node("embed", embed_node)
    graph.add_node("fanout", fanout_node)
    graph.add_node("synthesize", synthesize_node)
    graph.add_node("emit", emit_node)
    graph.set_entry_point("ingest")
    graph.add_edge("ingest", "parse")
    graph.add_edge("parse", "embed")
    graph.add_edge("embed", "fanout")
    graph.add_edge("fanout", "synthesize")
    graph.add_edge("synthesize", "emit")
    graph.add_edge("emit", END)
    return graph.compile()


GRAPH = build_graph()


async def run_pipeline(job_id: str, repo_url: str, role: str):
    initial: RepoPilotState = {
        "job_id": job_id, "repo_url": repo_url, "role": role,
        "repo_path": None, "repo_context": None, "parsed_files": [], "chunks": [],
        "findings": [], "plan": None, "status": "queued", "error": None,
    }
    from job_store import update_job, publish, get_job
    started = time.perf_counter()
    try:
        async with asyncio.timeout(settings.pipeline_timeout_seconds):
            async for event in GRAPH.astream(initial):
                for node_name, state in event.items():
                    progress = {"ingest": 15, "parse": 30, "embed": 45, "fanout": 70, "synthesize": 90, "emit": 100}.get(node_name, 0)
                    message = f"{node_name.capitalize()} complete"
                    await update_job(job_id, progress=progress, node=node_name, latest_message=message)
                    record = get_job(job_id)
                    await publish(job_id, {"event": "agent_progress", "node": node_name, "status": state.get("status"), "progress": progress, "latest_message": message, "agents": record.agents if record else {}})
                    yield event
        duration = time.perf_counter() - started
        from monitoring import mark_repo_analyzed
        mark_repo_analyzed(duration)
    except Exception as exc:
        await update_job(job_id, status="failed", latest_message="Analysis failed", error=type(exc).__name__)
        await publish(job_id, {"event": "error", "job_id": job_id, "message": "Repository analysis failed"})
        raise
