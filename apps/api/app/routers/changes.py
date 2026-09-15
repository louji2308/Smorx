from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..database import get_supabase

router = APIRouter(prefix="/api/changes", tags=["changes"])

class ChangeCreate(BaseModel):
    repository_id: str
    external_id: str
    title: str
    description: str = ""
    commit_sha: str = ""
    author: str = ""

@router.post("")
async def create_change(data: ChangeCreate):
    db = get_supabase()
    result = db.table("changes").insert({
        "repository_id": data.repository_id,
        "external_id": data.external_id,
        "title": data.title,
        "description": data.description,
        "commit_sha": data.commit_sha,
        "author": data.author,
        "status": "open",
    }).execute()
    return result.data[0]

@router.get("")
async def list_changes(repository_id: str | None = None):
    db = get_supabase()
    query = db.table("changes").select("*")
    if repository_id:
        query = query.eq("repository_id", repository_id)
    result = query.order("created_at", desc=True).execute()
    return result.data

@router.get("/{change_id}")
async def get_change(change_id: str):
    db = get_supabase()
    result = db.table("changes").select("*").eq("id", change_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Change not found")
    return result.data[0]
