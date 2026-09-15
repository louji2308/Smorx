from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..database import get_supabase

router = APIRouter(prefix="/api/projects", tags=["projects"])

class ProjectCreate(BaseModel):
    name: str
    slug: str
    description: str = ""

@router.post("")
async def create_project(data: ProjectCreate):
    db = get_supabase()
    result = db.table("projects").insert({
        "name": data.name,
        "slug": data.slug,
        "description": data.description,
    }).execute()
    return result.data[0]

@router.get("")
async def list_projects():
    db = get_supabase()
    result = db.table("projects").select("*").order("created_at", desc=True).execute()
    return result.data

@router.get("/{project_id}")
async def get_project(project_id: str):
    db = get_supabase()
    result = db.table("projects").select("*").eq("id", project_id).execute()
    if not result.data:
        raise HTTPException(status_code=404, detail="Project not found")
    return result.data[0]
