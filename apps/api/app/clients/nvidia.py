import httpx
import json
from .config import settings

NVIDIA_API = "https://integrate.api.nvidia.com/v1"

async def chat_completion(messages: list[dict], temperature: float = 0.3, max_tokens: int = 4096) -> str:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{NVIDIA_API}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.nvidia_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": settings.nvidia_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

async def extract_intents(codebase_context: str, change_description: str) -> list[dict]:
    prompt = f"""You are an expert software engineer analyzing a code change.

CODEBASE CONTEXT:
{codebase_context[:3000]}

CHANGE DESCRIPTION:
{change_description}

Extract the INTENTS (goals, requirements, constraints) from this change.
Return a JSON array of objects with these fields:
- statement: string (what this intent says)
- kind: "goal" | "constraint" | "requirement" | "assumption"
- priority: "critical" | "high" | "medium" | "low"
- source_ref: string (file or line reference)

Return ONLY valid JSON array, no markdown."""

    response = await chat_completion([{"role": "user", "content": prompt}], temperature=0.2)
    try:
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        return json.loads(response)
    except json.JSONDecodeError:
        return [{"statement": change_description, "kind": "goal", "priority": "high", "source_ref": ""}]

async def analyze_impact(codebase_context: str, intents: list[dict]) -> dict:
    intents_text = "\n".join(f"- {i['statement']} ({i['kind']})" for i in intents)
    prompt = f"""You are an expert software engineer analyzing the semantic impact of a code change.

CODEBASE CONTEXT:
{codebase_context[:3000]}

INTENTS:
{intents_text}

Analyze the impact. Return a JSON object with:
- surfaces: array of objects with path (string), direction ("breaks" | "modifies" | "extends" | "creates"), claim_ref (string), risk ("high" | "medium" | "low")
- risk_zones: array of objects with pattern (string), reason (string), severity ("critical" | "high" | "medium" | "low")
- summary: string

Return ONLY valid JSON, no markdown."""

    response = await chat_completion([{"role": "user", "content": prompt}], temperature=0.2)
    try:
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        return json.loads(response)
    except json.JSONDecodeError:
        return {"surfaces": [], "risk_zones": [], "summary": "Impact analysis could not be parsed"}

async def generate_verification_plan(intents: list[dict], impact: dict, codebase_context: str) -> list[dict]:
    intents_text = "\n".join(f"- {i['statement']}" for i in intents)
    surfaces_text = "\n".join(f"- {s['path']}: {s['direction']} (risk: {s['risk']})" for s in impact.get("surfaces", []))
    prompt = f"""You are an expert QA engineer designing a verification plan.

INTENTS:
{intents_text}

IMPACT SURFACES:
{surfaces_text}

CODEBASE CONTEXT:
{codebase_context[:2000]}

Generate verification cases. Return a JSON array of objects with:
- name: string
- kind: "unit" | "integration" | "e2e" | "security" | "performance" | "behavioral"
- description: string
- method: string (how to verify)
- expected: string
- threshold: number (0-1, confidence threshold)

Return ONLY valid JSON array, no markdown."""

    response = await chat_completion([{"role": "user", "content": prompt}], temperature=0.2)
    try:
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        return json.loads(response)
    except json.JSONDecodeError:
        return [{"name": "Basic verification", "kind": "unit", "description": "Verify the change works", "method": "Run tests", "expected": "All tests pass", "threshold": 0.8}]

async def make_decision(intents: list[dict], impact: dict, verification_results: list[dict]) -> dict:
    prompt = f"""You are an expert software architect making a deployment decision.

INTENTS: {json.dumps(intents[:5], indent=2)}
IMPACT SUMMARY: {impact.get('summary', 'N/A')}
VERIFICATION RESULTS: {json.dumps(verification_results[:10], indent=2)}

Make a decision. Return a JSON object with:
- verdict: "authorize" | "reject" | "conditional"
- confidence: number (0-1)
- rationale: string
- next_action: string

Return ONLY valid JSON, no markdown."""

    response = await chat_completion([{"role": "user", "content": prompt}], temperature=0.1)
    try:
        response = response.strip()
        if response.startswith("```"):
            response = response.split("```")[1]
            if response.startswith("json"):
                response = response[4:]
        return json.loads(response)
    except json.JSONDecodeError:
        return {"verdict": "conditional", "confidence": 0.7, "rationale": "Decision could not be parsed", "next_action": "Review manually"}
