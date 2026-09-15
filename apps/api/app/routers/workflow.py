from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..database import get_supabase
from ..clients.nvidia import extract_intents, analyze_impact, generate_verification_plan, make_decision
from ..clients.github import get_repo_analysis
from ..clients.nebius import execute_in_sandbox, clone_and_analyze, run_tests
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

    context = f"Repository: {analysis['name']}\nLanguages: {', '.join(analysis.get('languages', {}).keys())}\nFiles: {analysis.get('file_count', 0)}\nDirectories: {', '.join(analysis.get('directories', [])[:20])}"

    intents = await extract_intents(context, req.change_description or req.change_title)
    for intent in intents:
        db.table("claims").insert({
            "statement": intent["statement"],
            "kind": intent["kind"],
            "status": "observed",
            "confidence": 0.7,
        }).execute()

    impact = await analyze_impact(context, intents)
    for surface in impact.get("surfaces", []):
        db.table("behaviors").insert({
            "repository_id": repo["id"],
            "name": surface["path"],
            "description": f"{surface['direction']} by change",
            "category": "semantic_impact",
            "protected": surface["risk"] == "high",
        }).execute()

    return {
        "project": project,
        "repository": repo,
        "change": change,
        "constitution": constitution,
        "analysis": analysis,
        "intents": intents,
        "impact": impact,
    }

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
        result = await run_tests(req.repo_url, req.test_command, req.branch)
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
