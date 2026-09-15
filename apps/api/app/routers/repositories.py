from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..database import get_supabase
from ..clients.github import get_repo_analysis

router = APIRouter(prefix="/api/repositories", tags=["repositories"])

class RepositoryCreate(BaseModel):
    project_id: str
    name: str
    url: str
    default_branch: str = "main"

@router.post("")
async def create_repository(data: RepositoryCreate):
    db = get_supabase()
    result = db.table("repositories").insert({
        "project_id": data.project_id,
        "name": data.name,
        "url": data.url,
        "default_branch": data.default_branch,
        "vcs": "github",
    }).execute()
    return result.data[0]

@router.get("")
async def list_repositories(project_id: str | None = None):
    db = get_supabase()
    query = db.table("repositories").select("*")
    if project_id:
        query = query.eq("project_id", project_id)
    result = query.order("created_at", desc=True).execute()
    return result.data

@router.get("/{repo_id}")
async def get_repository(repo_id: str):
    db = get_supabase()
    result = db.table("repositories").select("*").eq("id", repo_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Repository not found")
    return result.data[0]

@router.post("/{repo_id}/analyze")
async def analyze_repository(repo_id: str):
    db = get_supabase()
    repo_result = db.table("repositories").select("*").eq("id", repo_id).execute()
    if not repo_result.data:
        raise HTTPException(status_code=404, detail="Repository not found")
    repo = repo_result.data[0]

    from urllib.parse import urlparse
    parsed = urlparse(repo["url"])
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2:
        raise HTTPException(status_code=400, detail="Invalid GitHub URL")
    owner, name = parts[0], parts[1]

    analysis = await get_repo_analysis(owner, name)

    db.table("repositories").update({
        "meta": analysis,
        "last_inspected_at": "now()",
    }).eq("id", repo_id).execute()

    return analysis
