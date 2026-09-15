from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import asyncio
from ..database import get_supabase
from ..clients.agent import AgentOrchestrator
from ..clients.github import get_repo_analysis
from ..clients.nebius import execute_in_sandbox
from urllib.parse import urlparse

router = APIRouter(prefix="/api/workflow", tags=["workflow"])

class StartWorkflowRequest(BaseModel):
    project_name: str
    repo_url: str
    change_title: str
    change_description: str = ""
    change_author: str = ""

@router.post("/start")
async def start_workflow(req: StartWorkflowRequest):
    db = get_supabase()

    project_result = db.table("projects").insert({
        "name": req.project_name,
        "slug": req.project_name.lower().replace(" ", "-"),
        "description": f"Automated analysis of {req.repo_url}",
    }).execute()
    project = project_result.data[0]

    parsed = urlparse(req.repo_url)
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")
    owner, name = parts[0], parts[1]

    analysis = await get_repo_analysis(owner, name)

    repo_result = db.table("repositories").insert({
        "project_id": project["id"],
        "name": name,
        "url": req.repo_url,
        "default_branch": analysis.get("default_branch", "main"),
        "vcs": "github",
        "meta": analysis,
        "last_inspected_at": "now()",
    }).execute()
    repo = repo_result.data[0]

    change_result = db.table("changes").insert({
        "repository_id": repo["id"],
        "external_id": "auto",
        "title": req.change_title,
        "description": req.change_description or req.change_title,
        "author": req.change_author,
        "status": "open",
    }).execute()
    change = change_result.data[0]

    constitution_result = db.table("constitutions").insert({
        "project_id": project["id"],
        "title": f"Constitution for {req.project_name}",
        "statement": f"Automated governance for {req.project_name}",
        "status": "active",
        "version": 1,
    }).execute()
    constitution = constitution_result.data[0]

    return {
        "project": project,
        "repository": repo,
        "change": change,
        "constitution": constitution,
        "analysis": analysis,
    }

class RunAgentRequest(BaseModel):
    task_id: str
    repo_url: str
    change_id: str

@router.post("/agent/run")
async def run_agent(req: RunAgentRequest):
    orchestrator = AgentOrchestrator(
        task_id=req.task_id,
        repo_url=req.repo_url,
        change_id=req.change_id,
    )

    async def event_stream():
        async for event in orchestrator.run():
            yield f"data: {json.dumps(event, default=str)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

class SandboxExecuteRequest(BaseModel):
    repo_url: str
    command: str
    branch: str = "main"
    timeout: int = 300

@router.post("/sandbox/execute")
async def sandbox_execute(req: SandboxExecuteRequest):
    try:
        result = await execute_in_sandbox(
            f"cd /tmp && git clone --depth 1 -b {req.branch} {req.repo_url} repo && cd repo && {req.command}",
            timeout=req.timeout,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SandboxTestRequest(BaseModel):
    repo_url: str
    test_command: str = "npm test"
    branch: str = "main"

@router.post("/sandbox/test")
async def sandbox_test(req: SandboxTestRequest):
    try:
        test_cmd = f"cd /tmp && git clone --depth 1 -b {req.branch} {req.repo_url} repo && cd repo && {req.test_command}"
        result = await execute_in_sandbox(test_cmd)
        db = get_supabase()
        db.table("executions").insert({
            "kind": "test",
            "command": req.test_command,
            "exit_code": result.get("exit_code"),
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "duration_ms": int(result.get("duration", 0) * 1000) if result.get("duration") else None,
            "status": "success" if result.get("exit_code") == 0 else "failed",
        }).execute()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
