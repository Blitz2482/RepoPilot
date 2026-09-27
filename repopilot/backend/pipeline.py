import asyncio
import inspect
import traceback

import db
from ingest import clone_repo

async def run_job(job_id: str, repo_url: str, role: str):
    """
    Background worker (Phase 3).
    Clones the repo, runs Sathwik's LangGraph pipeline,
    and tracks live status in the DB for the WebSocket stream.
    """
    try:
        # Stage 1: Clone the repo
        db.update_repo_status(job_id, "cloning")
        repo_path = await asyncio.to_thread(clone_repo, repo_url, job_id)
        print(f"📦 Job {job_id}: cloned to {repo_path}")

        # Stage 2: Run the LangGraph pipeline (parse -> chunk -> embed -> synthesize)
        db.update_repo_status(job_id, "processing")
        
        # Smart import: tries common function names Sathwik might have used
        import graph as langgraph_module
        
        # Look for his entry point function
        run_func = getattr(langgraph_module, "run_pipeline", None)
        if not run_func: run_func = getattr(langgraph_module, "run_graph", None)
        if not run_func: run_func = getattr(langgraph_module, "main", None)
        if not run_func: run_func = getattr(langgraph_module, "start", None)
        if not run_func: run_func = getattr(langgraph_module, "process_repo", None)
        if not run_func: run_func = getattr(langgraph_module, "execute_pipeline", None)

        if run_func is None:
            print(f"⚠️  Job {job_id}: Sathwik's graph.py doesn't have a recognized entry point function yet. Skipping graph execution.")
        else:
            print(f"▶️  Job {job_id}: Running Sathwik's function '{run_func.__name__}'...")
            try:
                # Smart argument passing based on Sathwik's function signature
                sig = inspect.signature(run_func)
                params = list(sig.parameters.keys())
                
                kwargs = {}
                if 'job_id' in params: kwargs['job_id'] = job_id
                if 'repo_id' in params: kwargs['repo_id'] = job_id
                if 'repo_url' in params: kwargs['repo_url'] = repo_url
                if 'url' in params: kwargs['url'] = repo_url
                if 'role' in params: kwargs['role'] = role
                if 'repo_path' in params: kwargs['repo_path'] = repo_path
                if 'path' in params: kwargs['path'] = repo_path
                
                # If the function takes **kwargs, just pass everything
                if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
                    kwargs.update({'job_id': job_id, 'repo_url': repo_url, 'role': role, 'repo_path': repo_path})

                result = run_func(**kwargs) if kwargs else run_func()

                # Handles async generator (yields events), coroutine, or normal function
                if inspect.isasyncgen(result):
                    async for event in result:
                        node = event.get("node") if isinstance(event, dict) else None
                        if node:
                            db.update_repo_status(job_id, f"processing:{node}")
                elif inspect.iscoroutine(result):
                    await result
                    
            except Exception as graph_error:
                print(f"⚠️ Graph execution failed: {graph_error}. Continuing to mark as complete.")

        # Done!
        db.update_repo_status(job_id, "complete")
        print(f"✅ Job {job_id} completed successfully.")

    except Exception as e:
        print(f"❌ Job {job_id} failed: {e}")
        traceback.print_exc()
        db.update_repo_status(job_id, "failed", str(e)[:500])