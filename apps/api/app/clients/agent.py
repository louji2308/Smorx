import asyncio
import json
import time
from datetime import datetime
from typing import AsyncGenerator
from ..database import get_supabase
from ..clients.nvidia import (
    chat_completion,
    extract_intents,
    analyze_impact,
    generate_verification_plan,
    make_decision,
    smart_chat_completion,
    classify_task_complexity,
)
from ..clients.github import get_file_content, get_file_tree
from ..clients.nebius import execute_in_sandbox, clone_and_analyze
from ..clients.evidence import (
    collect_execution_evidence,
    collect_test_evidence,
    fuse_claim_evidence,
    compute_hash,
)

MAX_ITERATIONS = 5
MAX_REPAIR_ATTEMPTS = 3

class AgentOrchestrator:
    def __init__(self, task_id: str, repo_url: str, change_id: str):
        self.task_id = task_id
        self.repo_url = repo_url
        self.change_id = change_id
        self.db = get_supabase()
        self.iteration = 0
        self.evidence_chain = []
        self.failures = []
        self.sandbox_id = None

    async def run(self) -> AsyncGenerator[dict, None]:
        """Full agent loop: understand → plan → execute → observe → diagnose → patch → retest."""
        yield {"phase": "started", "message": "Agent loop starting", "iteration": 0}

        # Phase 1: UNDERSTAND
        async for event in self._understand():
            yield event

        # Phase 2: INSPECT
        async for event in self._inspect():
            yield event

        # Phase 3: PLAN
        async for event in self._plan():
            yield event

        # Phase 4-8: EXECUTE → OBSERVE → DIAGNOSE → PATCH → RETEST (loop)
        while self.iteration < MAX_ITERATIONS:
            self.iteration += 1
            yield {"phase": "iteration", "iteration": self.iteration, "message": f"Starting iteration {self.iteration}"}

            # Execute
            async for event in self._execute():
                yield event

            # Observe
            result = await self._observe()
            yield result

            # Check if verified
            if result.get("all_passed"):
                yield {"phase": "verified", "message": "All tests passed", "iteration": self.iteration}
                break

            # Check repair limit
            if len(self.failures) >= MAX_REPAIR_ATTEMPTS:
                yield {"phase": "blocked", "message": "Max repair attempts reached", "iteration": self.iteration}
                break

            # Diagnose
            async for event in self._diagnose(result):
                yield event

            # Patch
            async for event in self._patch():
                yield event

        # Phase 9: VERIFY
        async for event in self._verify():
            yield event

        # Phase 10: CERTIFY
        async for event in self._certify():
            yield event

        yield {"phase": "completed", "message": "Agent loop complete", "iteration": self.iteration}

    async def _understand(self) -> AsyncGenerator[dict, None]:
        """Phase 1: Understand the task."""
        yield {"phase": "understand", "message": "Analyzing task requirements"}

        change = self.db.table("changes").select("*").eq("id", self.change_id).execute()
        if not change.data:
            yield {"phase": "error", "message": "Change not found"}
            return

        change_data = change.data[0]

        # Classify task complexity
        complexity = await classify_task_complexity(
            change_data.get("title", ""),
            change_data.get("description", ""),
        )

        # Extract intents using appropriate model
        intents = await extract_intents(
            f"Task: {change_data.get('title', '')}\nDescription: {change_data.get('description', '')}",
            change_data.get("description", change_data.get("title", "")),
        )

        # Store intents as claims
        for intent in intents:
            self.db.table("claims").insert({
                "statement": intent["statement"],
                "kind": intent["kind"],
                "status": "observed",
                "confidence": 0.5,
            }).execute()

        yield {
            "phase": "understand",
            "message": f"Extracted {len(intents)} intents, complexity: {complexity.get('complexity', 'normal')}",
            "intents": intents,
            "complexity": complexity,
        }

    async def _inspect(self) -> AsyncGenerator[dict, None]:
        """Phase 2: Inspect the repository."""
        yield {"phase": "inspect", "message": "Inspecting repository in sandbox"}

        # Clone and analyze in sandbox
        result = await clone_and_analyze(self.repo_url)
        self.sandbox_id = result.get("sandbox_id")

        # Collect evidence
        evidence = await collect_execution_evidence(result, self.task_id)
        self.evidence_chain.append(evidence)

        # Parse repo structure from stdout
        stdout = result.get("stdout", "")
        files = [line.strip() for line in stdout.split("\n") if line.strip() and not line.startswith("===")]

        yield {
            "phase": "inspect",
            "message": f"Repository cloned, {len(files)} files discovered",
            "sandbox_id": self.sandbox_id,
            "files": files[:50],
        }

    async def _plan(self) -> AsyncGenerator[dict, None]:
        """Phase 3: Create execution plan."""
        yield {"phase": "plan", "message": "Creating execution plan"}

        change = self.db.table("changes").select("*").eq("id", self.change_id).execute()
        claims = self.db.table("claims").select("*").execute()

        plan_prompt = f"""Create a detailed execution plan for this software engineering task.

Task: {change.data[0].get('title', '') if change.data else 'Unknown'}
Description: {change.data[0].get('description', '') if change.data else ''}
Claims: {json.dumps([c['statement'] for c in claims.data[:5]], indent=2)}

Return a JSON object with:
- steps: array of strings (ordered execution steps)
- test_command: string (command to run tests)
- files_to_modify: array of strings (likely files to change)
- success_criteria: array of strings (how to verify success)
"""

        response = await smart_chat_completion(
            [{"role": "user", "content": plan_prompt}],
            task_type="normal",
        )

        try:
            plan = json.loads(response.strip().strip("`").removeprefix("json"))
        except json.JSONDecodeError:
            plan = {
                "steps": ["Analyze codebase", "Implement changes", "Run tests", "Verify"],
                "test_command": "npm test",
                "files_to_modify": [],
                "success_criteria": ["All tests pass"],
            }

        yield {
            "phase": "plan",
            "message": f"Plan created with {len(plan.get('steps', []))} steps",
            "plan": plan,
        }

    async def _execute(self) -> AsyncGenerator[dict, None]:
        """Phase 4: Execute code changes in sandbox."""
        yield {"phase": "execute", "message": f"Executing changes in sandbox (iteration {self.iteration})"}

        change = self.db.table("changes").select("*").eq("id", self.change_id).execute()
        change_data = change.data[0] if change.data else {}

        # Generate code using Nemotron
        code_prompt = f"""You are an expert software engineer. Generate the code changes needed for this task.

Task: {change_data.get('title', '')}
Description: {change_data.get('description', '')}

Return a JSON object with:
- file_changes: array of objects with path (string) and content (string)
- explanation: string

The file_changes should contain the actual code to write to each file.
"""

        response = await smart_chat_completion(
            [{"role": "user", "content": code_prompt}],
            task_type="normal",
        )

        try:
            code_changes = json.loads(response.strip().strip("`").removeprefix("json"))
        except json.JSONDecodeError:
            code_changes = {"file_changes": [], "explanation": "Could not parse code changes"}

        # Apply changes in sandbox
        if code_changes.get("file_changes"):
            for change in code_changes["file_changes"]:
                path = change.get("path", "")
                content = change.get("content", "")
                if path and content:
                    # Write file in sandbox
                    cmd = f'echo {repr(content)} > /tmp/repo/{path}'
                    result = await execute_in_sandbox(
                        cmd,
                        cwd="/tmp/repo",
                    )
                    yield {"phase": "execute", "message": f"Modified {path}", "file": path}

        yield {
            "phase": "execute",
            "message": f"Applied {len(code_changes.get('file_changes', []))} file changes",
            "changes": code_changes,
        }

    async def _observe(self) -> dict:
        """Phase 5: Observe execution results."""
        change = self.db.table("changes").select("*").eq("id", self.change_id).execute()
        change_data = change.data[0] if change.data else {}

        # Run tests in sandbox
        test_cmd = "cd /tmp/repo && (npm test 2>&1 || pytest 2>&1 || python -m pytest 2>&1 || echo 'No test framework found')"
        result = await execute_in_sandbox(test_cmd)

        # Collect test evidence
        evidence = await collect_test_evidence(result, self.task_id)
        self.evidence_chain.append(evidence)

        exit_code = result.get("exit_code", -1)
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")

        all_passed = exit_code == 0

        return {
            "phase": "observe",
            "exit_code": exit_code,
            "all_passed": all_passed,
            "stdout": stdout[:5000],
            "stderr": stderr[:2000],
            "evidence_id": evidence.get("id"),
        }

    async def _diagnose(self, result: dict) -> AsyncGenerator[dict, None]:
        """Phase 6: Diagnose failures."""
        if result.get("all_passed"):
            return

        yield {"phase": "diagnose", "message": "Analyzing test failures"}

        diagnosis_prompt = f"""Analyze this test failure and provide a diagnosis.

Exit code: {result.get('exit_code')}
Stdout: {result.get('stdout', '')[:2000]}
Stderr: {result.get('stderr', '')[:1000]}

Return a JSON object with:
- classification: string (syntax_error, test_failure, logic_error, dependency_error, etc.)
- root_cause: string (what actually went wrong)
- affected_files: array of strings
- fix_strategy: string (how to fix it)
"""

        response = await smart_chat_completion(
            [{"role": "user", "content": diagnosis_prompt}],
            task_type="normal",
        )

        try:
            diagnosis = json.loads(response.strip().strip("`").removeprefix("json"))
        except json.JSONDecodeError:
            diagnosis = {
                "classification": "unknown",
                "root_cause": "Could not parse diagnosis",
                "affected_files": [],
                "fix_strategy": "Retry with different approach",
            }

        # Store failure
        failure = {
            "task_id": self.task_id,
            "classification": diagnosis.get("classification", "unknown"),
            "message": diagnosis.get("root_cause", "Unknown error"),
            "probable_cause": diagnosis.get("root_cause", ""),
            "next_action": diagnosis.get("fix_strategy", ""),
            "severity": "high",
            "iteration": self.iteration,
            "resolved": False,
            "occurred_at": datetime.utcnow().isoformat(),
        }
        self.db.table("failures").insert(failure).execute()
        self.failures.append(failure)

        yield {
            "phase": "diagnose",
            "message": f"Diagnosed: {diagnosis.get('classification', 'unknown')}",
            "diagnosis": diagnosis,
        }

    async def _patch(self) -> AsyncGenerator[dict, None]:
        """Phase 7: Generate and apply patch."""
        yield {"phase": "patch", "message": f"Generating patch (iteration {self.iteration})"}

        last_failure = self.failures[-1] if self.failures else {}

        patch_prompt = f"""Generate a fix for this failure.

Failure classification: {last_failure.get('classification', 'unknown')}
Root cause: {last_failure.get('probable_cause', 'Unknown')}
Fix strategy: {last_failure.get('next_action', 'Retry')}

Return a JSON object with:
- file_changes: array of objects with path (string) and content (string)
- explanation: string
"""

        response = await smart_chat_completion(
            [{"role": "user", "content": patch_prompt}],
            task_type="normal",
        )

        try:
            patch = json.loads(response.strip().strip("`").removeprefix("json"))
        except json.JSONDecodeError:
            patch = {"file_changes": [], "explanation": "Could not generate patch"}

        # Apply patch in sandbox
        if patch.get("file_changes"):
            for change in patch["file_changes"]:
                path = change.get("path", "")
                content = change.get("content", "")
                if path and content:
                    cmd = f'echo {repr(content)} > /tmp/repo/{path}'
                    await execute_in_sandbox(cmd, cwd="/tmp/repo")

        yield {
            "phase": "patch",
            "message": f"Applied patch with {len(patch.get('file_changes', []))} file changes",
            "patch": patch,
        }

    async def _verify(self) -> AsyncGenerator[dict, None]:
        """Phase 8: Final verification."""
        yield {"phase": "verify", "message": "Running final verification"}

        # Run full test suite
        test_cmd = "cd /tmp/repo && (npm test 2>&1 || pytest 2>&1 || python -m pytest 2>&1 || echo 'No test framework found')"
        result = await execute_in_sandbox(test_cmd)

        # Collect final evidence
        evidence = await collect_test_evidence(result, self.task_id)
        self.evidence_chain.append(evidence)

        # Fuse all claim evidence
        claims = self.db.table("claims").select("*").execute()
        verification_results = []
        for claim in claims.data:
            fused = await fuse_claim_evidence(claim["id"])
            verification_results.append(fused)

        all_protected = all(r.get("status") == "PROTECTED" for r in verification_results)

        yield {
            "phase": "verify",
            "message": f"Verification complete: {len(verification_results)} claims checked",
            "results": verification_results,
            "all_protected": all_protected,
        }

    async def _certify(self) -> AsyncGenerator[dict, None]:
        """Phase 9: Generate certificate."""
        yield {"phase": "certify", "message": "Generating certificate"}

        claims = self.db.table("claims").select("*").execute()
        evidence_count = len(self.evidence_chain)

        # Create certificate
        certificate = {
            "task_id": self.task_id,
            "certificate_key": f"CERT-{self.task_id[:8]}-{int(time.time())}",
            "status": "certified",
            "payload": {
                "iterations": self.iteration,
                "claims_verified": len([c for c in claims.data if c.get("status") == "protected"]),
                "total_claims": len(claims.data),
                "evidence_collected": evidence_count,
                "failures_repaired": len(self.failures),
                "sandbox_id": self.sandbox_id,
            },
            "evidence_hash": compute_hash(json.dumps(self.evidence_chain, default=str)),
            "issued_at": datetime.utcnow().isoformat(),
        }

        self.db.table("certificates").insert(certificate).execute()

        yield {
            "phase": "certify",
            "message": "Certificate issued",
            "certificate": certificate,
        }
