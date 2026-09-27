import asyncio
from pipeline import run_job
import uuid
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Optional

import db  # CRITICAL: Import your database layer

router = APIRouter(prefix="/api", tags=["api"])

# --- Pydantic Models ---
class RepoSubmitRequest(BaseModel):
    repo_url: str
    role: str

class QuestionRequest(BaseModel):
    question: str

class Citation(BaseModel):
    path: str
    start: int
    end: int

class AskResponse(BaseModel):
    answer: str
    citations: List[Citation]

# --- Endpoints ---

@router.post("/repos")
async def submit_repo(request: RepoSubmitRequest):
    """Accept a repo URL and role, save to DB, return a job_id."""
    if not request.repo_url.startswith("https://github.com/"):
        raise HTTPException(status_code=400, detail="Invalid GitHub URL.")
    
    job_id = str(uuid.uuid4())
    
    # Save to Supabase (Real DB)
    try:
        db.create_repo(url=request.repo_url, job_id=job_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
    # 🔥 PHASE 3 ADDITION: Fire the background pipeline (non-blocking!)
    asyncio.create_task(run_job(job_id, request.repo_url, request.role))
    
    return {"job_id": job_id, "status": "queued"}

@router.get("/repos/{job_id}")
async def get_repo_status(job_id: str):
    """Get the status of a submitted job from DB."""
    repo = db.get_repo(job_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Job not found")
    return repo

@router.get("/repos/{job_id}/plan")
async def get_plan(job_id: str):
    """Get the generated onboarding plan from DB."""
    plan = db.get_plan(job_id)
    
    if not plan:
        return {"job_id": job_id, "status": "processing", "plan": None}
        
    return {"job_id": job_id, "status": "complete", "plan": plan}

@router.get("/repos/{job_id}/tour")
async def get_tour(job_id: str):
    """Get the 8-step code tour."""
    plan = db.get_plan(job_id)
    
    if not plan:
        return {"job_id": job_id, "tour_steps": []}
    
    # Extract tour_steps if they exist in the plan JSON
    tour_steps = plan.get("tour_steps", []) if isinstance(plan, dict) else []
    return {"job_id": job_id, "tour_steps": tour_steps}

@router.post("/repos/{job_id}/ask", response_model=AskResponse)
async def ask_question(job_id: str, request: QuestionRequest):
    """Grounded Q&A endpoint."""
    repo = db.get_repo(job_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Job not found")
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty")
        
    # Call the new async qa.py pipeline
    from qa import answer_question
    
    # MUST use await here because answer_question is async
    result = await answer_question(job_id, request.question)
    
    return AskResponse(
        answer=result["answer"],
        citations=[Citation(**c) for c in result["citations"]]
    )

# --- WebSocket Endpoint (PHASE 3 UPGRADE) ---

@router.websocket("/repos/{job_id}/stream")
async def stream_progress(websocket: WebSocket, job_id: str):
    """Live progress stream — polls DB status, never crashes."""
    await websocket.accept()
    last_status = None
    try:
        while True:
            repo = db.get_repo(job_id)
            if not repo:
                await websocket.send_json({"event": "error", "message": "Job not found"})
                break
                
            status = repo.get("status", "queued")
            
            # Only send an update if the status actually changed
            if status != last_status:
                await websocket.send_json({"event": "progress", "node": status, "status": status})
                last_status = status
                
            # Stop the stream when the job finishes or fails
            if status in ("complete", "failed"):
                await websocket.send_json({
                    "event": status,
                    "job_id": job_id,
                    "error": repo.get("error_message")
                })
                break
                
            await asyncio.sleep(2) # Poll the DB every 2 seconds
            
    except WebSocketDisconnect:
        print(f"Client disconnected for job {job_id}")
    except Exception as e:
        await websocket.send_json({"event": "error", "message": str(e)})
    finally:
        await websocket.close()