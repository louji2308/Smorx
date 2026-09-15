import hashlib
import json
from datetime import datetime
from ..database import get_supabase

def compute_hash(data: str) -> str:
    """Compute SHA-256 hash of data for integrity."""
    return hashlib.sha256(data.encode()).hexdigest()

async def collect_execution_evidence(
    execution_result: dict,
    task_id: str,
    run_id: str = None,
    claim_id: str = None,
    verification_case_id: str = None,
) -> dict:
    """Collect evidence from a sandbox execution result."""
    # Normalize the execution result into an evidence record
    evidence = {
        "task_id": task_id,
        "run_id": run_id,
        "type": "execution",
        "source": "nebius_sandbox",
        "occurred_at": datetime.utcnow().isoformat(),
        "provenance": f"sandbox:{execution_result.get('sandbox_id', 'unknown')}",
        "machine_result": {
            "exit_code": execution_result.get("exit_code"),
            "stdout": execution_result.get("stdout", "")[:10000],  # truncate
            "stderr": execution_result.get("stderr", "")[:5000],
            "duration": execution_result.get("duration"),
            "status": execution_result.get("status"),
        },
        "hash": compute_hash(json.dumps(execution_result, default=str)),
    }
    if claim_id:
        evidence["claim_id"] = claim_id
    if verification_case_id:
        evidence["verification_case_id"] = verification_case_id
    
    # Store in Supabase
    db = get_supabase()
    result = db.table("evidence").insert(evidence).execute()
    return result.data[0]

async def collect_test_evidence(
    test_result: dict,
    task_id: str,
    claim_id: str = None,
) -> dict:
    """Collect evidence from test execution."""
    passed = test_result.get("stdout", "").count("PASSED") + test_result.get("stdout", "").count("passed")
    failed = test_result.get("stdout", "").count("FAILED") + test_result.get("stdout", "").count("failed")
    exit_code = test_result.get("exit_code", -1)
    
    evidence = {
        "task_id": task_id,
        "type": "test_execution",
        "source": "nebius_sandbox",
        "occurred_at": datetime.utcnow().isoformat(),
        "provenance": f"sandbox:test:{test_result.get('sandbox_id', 'unknown')}",
        "machine_result": {
            "exit_code": exit_code,
            "tests_passed": passed,
            "tests_failed": failed,
            "stdout": test_result.get("stdout", "")[:10000],
            "stderr": test_result.get("stderr", "")[:5000],
            "duration": test_result.get("duration"),
            "all_passed": exit_code == 0,
        },
        "hash": compute_hash(json.dumps(test_result, default=str)),
    }
    if claim_id:
        evidence["claim_id"] = claim_id
    
    db = get_supabase()
    result = db.table("evidence").insert(evidence).execute()
    return result.data[0]

async def fuse_claim_evidence(claim_id: str) -> dict:
    """Fuse all evidence for a claim and determine its status."""
    db = get_supabase()
    
    # Get claim
    claim = db.table("claims").select("*").eq("id", claim_id).execute()
    if not claim.data:
        return {"status": "not_found"}
    
    # Get all evidence for this claim
    evidence_list = db.table("evidence").select("*").eq("claim_id", claim_id).execute()
    
    if not evidence_list.data:
        return {"status": "no_evidence", "confidence": 0}
    
    # Calculate fused confidence
    total_confidence = 0
    has_failure = False
    has_success = False
    
    for ev in evidence_list.data:
        machine_result = ev.get("machine_result", {})
        if machine_result.get("exit_code") == 0 or machine_result.get("all_passed"):
            has_success = True
            total_confidence += 0.3
        else:
            has_failure = True
            total_confidence += 0.1
    
    # Normalize confidence
    confidence = min(total_confidence / len(evidence_list.data), 1.0)
    
    # Determine status
    if has_failure and not has_success:
        status = "VIOLATED"
    elif has_success and not has_failure:
        status = "PROTECTED"
    elif has_success and has_failure:
        status = "UNVERIFIED"  # Mixed results
    else:
        status = "OBSERVED"
    
    # Update claim
    db.table("claims").update({
        "status": status.lower(),
        "confidence": confidence,
    }).eq("id", claim_id).execute()
    
    return {
        "claim_id": claim_id,
        "status": status,
        "confidence": confidence,
        "evidence_count": len(evidence_list.data),
        "has_success": has_success,
        "has_failure": has_failure,
    }

async def calculate_behavioral_delta(
    task_id: str,
    change_id: str,
    claim_id: str,
    behavior_id: str,
    baseline_value: str,
    candidate_value: str,
) -> dict:
    """Calculate the behavioral delta between baseline and candidate."""
    # Calculate magnitude
    if baseline_value == candidate_value:
        magnitude = 0
        direction = "unchanged"
    elif candidate_value > baseline_value:
        magnitude = (float(candidate_value) - float(baseline_value)) / max(float(baseline_value), 1)
        direction = "increased"
    else:
        magnitude = (float(baseline_value) - float(candidate_value)) / max(float(baseline_value), 1)
        direction = "decreased"
    
    delta = {
        "task_id": task_id,
        "change_id": change_id,
        "claim_id": claim_id,
        "behavior_id": behavior_id,
        "metric": "behavioral_change",
        "baseline_value": baseline_value,
        "candidate_value": candidate_value,
        "magnitude": magnitude,
        "direction": direction,
        "category": "behavioral_delta",
        "description": f"Behavior changed from {baseline_value} to {candidate_value}",
        "observed": True,
    }
    
    db = get_supabase()
    result = db.table("behavioral_deltas").insert(delta).execute()
    return result.data[0]
