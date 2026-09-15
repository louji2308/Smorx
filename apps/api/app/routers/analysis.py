from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from ..database import get_supabase
from ..clients.nvidia import extract_intents, analyze_impact, generate_verification_plan, make_decision
from ..clients.github import get_file_content

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

class AnalyzeRequest(BaseModel):
    change_id: str

def build_codebase_context(repo_meta: dict, files: list[str] | None = None) -> str:
    lines = []
    lines.append(f"Repository: {repo_meta.get('name', 'unknown')}")
    lines.append(f"Languages: {', '.join(repo_meta.get('languages', {}).keys())}")
    lines.append(f"Files: {repo_meta.get('file_count', 0)}")
    lines.append(f"Directories: {', '.join(repo_meta.get('directories', [])[:20])}")
    lines.append(f"Recent commits:")
    for c in repo_meta.get("recent_commits", [])[:5]:
        lines.append(f"  - {c['sha']}: {c['message']}")
    return "\n".join(lines)

@router.post("/intents")
async def analyze_intents(req: AnalyzeRequest):
    db = get_supabase()
    change = db.table("changes").select("*, repositories(*)").eq("id", req.change_id).execute()
    if not change.data:
        raise HTTPException(status_code=404, detail="Change not found")
    change_data = change.data[0]
    repo_meta = change_data.get("repositories", {}).get("meta", {})

    context = build_codebase_context(repo_meta)
    intents = await extract_intents(context, change_data.get("description", change_data.get("title", "")))

    for i, intent in enumerate(intents):
        db.table("claims").insert({
            "statement": intent["statement"],
            "kind": intent["kind"],
            "status": "observed",
            "confidence": 0.7,
        }).execute()

    return {"intents": intents, "count": len(intents)}

@router.post("/impact")
async def analyze_impact_route(req: AnalyzeRequest):
    db = get_supabase()
    change = db.table("changes").select("*, repositories(*)").eq("id", req.change_id).execute()
    if not change.data:
        raise HTTPException(status_code=404, detail="Change not found")
    change_data = change.data[0]
    repo_meta = change_data.get("repositories", {}).get("meta", {})

    context = build_codebase_context(repo_meta)

    claims = db.table("claims").select("*").execute()
    intents = [{"statement": c["statement"], "kind": c["kind"]} for c in claims.data]

    impact = await analyze_impact(context, intents if intents else [{"statement": change_data.get("title", ""), "kind": "goal"}])

    for surface in impact.get("surfaces", []):
        db.table("behaviors").insert({
            "repository_id": change_data["repository_id"],
            "name": surface["path"],
            "description": f"{surface['direction']} by change",
            "category": "semantic_impact",
            "protected": surface["risk"] == "high",
        }).execute()

    for zone in impact.get("risk_zones", []):
        db.table("risk_zones").insert({
            "repository_id": change_data["repository_id"],
            "path_pattern": zone["pattern"],
            "reason": zone["reason"],
            "severity": zone["severity"],
            "score": 0.8 if zone["severity"] == "high" else 0.5,
        }).execute()

    return impact

@router.post("/verification")
async def generate_verification(req: AnalyzeRequest):
    db = get_supabase()
    change = db.table("changes").select("*, repositories(*)").eq("id", req.change_id).execute()
    if not change.data:
        raise HTTPException(status_code=404, detail="Change not found")
    change_data = change.data[0]
    repo_meta = change_data.get("repositories", {}).get("meta", {})

    context = build_codebase_context(repo_meta)
    claims = db.table("claims").select("*").execute()
    intents = [{"statement": c["statement"], "kind": c["kind"]} for c in claims.data]

    behaviors = db.table("behaviors").select("*").eq("repository_id", change_data["repository_id"]).execute()
    impact = {"surfaces": [{"path": b["name"], "direction": "modifies", "risk": "medium"} for b in behaviors.data]}

    cases = await generate_verification_plan(intents if intents else [{"statement": change_data.get("title", ""), "kind": "goal"}], impact, context)

    plan_result = db.table("verification_plans").insert({
        "change_id": req.change_id,
        "title": f"VP-{change_data.get('external_id', 'new')}",
        "strategy": {"approach": "comprehensive", "modalities": ["unit", "integration", "e2e", "behavioral"]},
        "verification_contract": {"cases": len(cases)},
        "status": "draft",
        "owner_scope": "system",
        "created_by": "agent",
    }).execute()

    plan_id = plan_result.data[0]["id"]

    for case in cases:
        db.table("verification_cases").insert({
            "verification_plan_id": plan_id,
            "change_id": req.change_id,
            "name": case["name"],
            "kind": case["kind"],
            "description": case["description"],
            "method": case["method"],
            "expected": case["expected"],
            "threshold": case.get("threshold", 0.8),
            "status": "pending",
            "independent": True,
        }).execute()

    return {"plan_id": plan_id, "cases": cases, "count": len(cases)}

@router.post("/decision")
async def make_decision_route(req: AnalyzeRequest):
    db = get_supabase()
    change = db.table("changes").select("*, repositories(*)").eq("id", req.change_id).execute()
    if not change.data:
        raise HTTPException(status_code=404, detail="Change not found")

    claims = db.table("claims").select("*").execute()
    intents = [{"statement": c["statement"], "kind": c["kind"]} for c in claims.data]

    behaviors = db.table("behaviors").select("*").execute()
    impact = {"summary": f"{len(behaviors.data)} behaviors analyzed", "surfaces": []}

    verification_results = [{"name": v["name"], "status": v["status"]} for v in db.table("verification_cases").select("*").execute().data]

    decision = await make_decision(intents if intents else [{"statement": "analyze change", "kind": "goal"}], impact, verification_results)

    return decision
