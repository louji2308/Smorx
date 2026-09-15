import httpx
import json
from .config import settings

NVIDIA_API = "https://integrate.api.nvidia.com/v1"

async def chat_completion(
    messages: list[dict],
    temperature: float = 0.3,
    max_tokens: int = 4096,
    model: str | None = None,
) -> str:
    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{NVIDIA_API}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.nvidia_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model or settings.nvidia_model,
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


# ─── Model Routing System ───────────────────────────────────────────────────────
# Routes tasks to the appropriate Nemotron variant based on complexity.

MODEL_LIGHTNING = "nvidia/llama-3.1-nemotron-3.5-lightning-30b-a3b"
MODEL_SUPER = "nvidia/llama-3.1-nemotron-3-super-120b"
MODEL_ULTRA = "nvidia/llama-3.1-nemotron-3-ultra-550b"


async def classify_task_complexity(task_description: str, context: str) -> str:
    """Use Nemotron Lightning to classify task complexity as simple, normal, or hard.

    Returns one of: "simple", "normal", "hard".
    """
    prompt = f"""Classify the complexity of the following task. Return ONLY a JSON object with two keys:
- "complexity": one of "simple", "normal", or "hard"
- "reason": a brief explanation of why

RULES:
- "simple": repo summary, file identification, command interpretation, single-line edits, straightforward lookups.
- "normal": coding decisions, debugging, multi-file reasoning, refactoring, API integrations, moderate architectural choices.
- "hard": difficult root-cause analysis, architectural changes, ambiguous failures, cross-system reasoning, final synthesis, security-critical decisions.

TASK:
{task_description}

CONTEXT:
{context[:2000]}

Return ONLY valid JSON, no markdown."""

    response = await chat_completion(
        [{"role": "user", "content": prompt}],
        model=MODEL_LIGHTNING,
        temperature=0.1,
        max_tokens=256,
    )
    try:
        cleaned = response.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        parsed = json.loads(cleaned)
        complexity = parsed.get("complexity", "normal")
        if complexity not in ("simple", "normal", "hard"):
            return "normal"
        return complexity
    except (json.JSONDecodeError, AttributeError):
        return "normal"


def get_model_for_task(complexity: str) -> str:
    """Map a complexity level to the corresponding Nemotron model ID."""
    routing_table = {
        "simple": MODEL_LIGHTNING,
        "normal": MODEL_SUPER,
        "hard": MODEL_ULTRA,
    }
    return routing_table.get(complexity, MODEL_SUPER)


async def smart_chat_completion(
    messages: list[dict],
    task_type: str = "normal",
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> str:
    """Route a chat completion to the appropriate Nemotron model.

    Args:
        messages: OpenAI-format message list.
        task_type: One of "simple", "normal", "hard", or "auto".
                   When "auto", the system uses Lightning to classify first.
        temperature: Sampling temperature.
        max_tokens: Maximum tokens in the response.

    Returns:
        The assistant message content string.
    """
    if task_type == "auto":
        last_user_msg = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                last_user_msg = msg.get("content", "")
                break
        context = "\n".join(
            m.get("content", "") for m in messages[:-1] if m.get("role") == "system"
        )
        complexity = await classify_task_complexity(last_user_msg, context)
    else:
        complexity = task_type

    model = get_model_for_task(complexity)

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(
            f"{NVIDIA_API}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.nvidia_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]
