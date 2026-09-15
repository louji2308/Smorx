import httpx
import time
import json
from ..config import settings

NEBIUS_API = "https://api.tokenfactory.nebius.com/sandboxes"

async def get_headers() -> dict:
    return {
        "Authorization": f"Bearer {settings.nebius_api_key}",
        "Project": settings.nebius_project_id,
        "Content-Type": "application/json",
    }

async def whoami() -> dict:
    async with httpx.AsyncClient() as client:
        headers = await get_headers()
        resp = await client.get(f"{NEBIUS_API}/whoami", headers=headers)
        resp.raise_for_status()
        return resp.json()

async def spawn_instance(
    command: str,
    image: str = "tag:ubuntu:latest",
    cwd: str = "",
    env: dict | None = None,
    timeout: int = 300,
    shell: bool = True,
) -> dict:
    body = {
        "command": command,
        "image": image,
        "shell": shell,
        "timeout": timeout,
    }
    if cwd:
        body["cwd"] = cwd
    if env:
        body["env"] = env

    async with httpx.AsyncClient() as client:
        headers = await get_headers()
        resp = await client.post(f"{NEBIUS_API}/instances", headers=headers, json=body)
        resp.raise_for_status()
        return resp.json()

async def get_operation(operation_id: str, inflight: bool = False) -> dict:
    async with httpx.AsyncClient() as client:
        headers = await get_headers()
        url = f"{NEBIUS_API}/operations/{operation_id}"
        if inflight:
            url += "?inflight=1"
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        return resp.json()

async def wait_for_operation(operation_id: str, max_wait: int = 600, poll_interval: int = 5) -> dict:
    start = time.time()
    while time.time() - start < max_wait:
        op = await get_operation(operation_id, inflight=True)
        status = op.get("status")
        if status in ("SUCCESS", "FAILED", "CANCELLED"):
            return op
        await asyncio.sleep(poll_interval)
    raise TimeoutError(f"Operation {operation_id} did not complete within {max_wait}s")

async def execute_in_sandbox(
    command: str,
    image: str = "tag:ubuntu:latest",
    cwd: str = "",
    env: dict | None = None,
    timeout: int = 300,
) -> dict:
    instance = await spawn_instance(command, image, cwd, env, timeout)
    operation_id = instance.get("uuid")
    if not operation_id:
        raise ValueError("No operation ID returned from spawn")

    result = await wait_for_operation(operation_id)

    return {
        "sandbox_id": operation_id,
        "status": result.get("status"),
        "exit_code": result.get("result", {}).get("exit_code"),
        "stdout": result.get("result", {}).get("stdout", ""),
        "stderr": result.get("result", {}).get("stderr", ""),
        "duration": result.get("duration"),
        "image_uuid": result.get("result_image_uuid"),
    }

async def clone_and_analyze(repo_url: str, branch: str = "main") -> dict:
    setup_cmd = f"""
cd /tmp && git clone --depth 1 -b {branch} {repo_url} repo && cd repo && \
echo "=== DIRECTORY STRUCTURE ===" && find . -maxdepth 2 -type f | head -50 && \
echo "=== PACKAGE FILES ===" && (cat package.json 2>/dev/null || cat requirements.txt 2>/dev/null || cat Cargo.toml 2>/dev/null || echo "No package file found") && \
echo "=== LANGUAGES ===" && find . -type f -name "*.py" -o -name "*.ts" -o -name "*.js" -o -name "*.rs" -o -name "*.go" | head -20
"""
    return await execute_in_sandbox(setup_cmd, timeout=120)

async def run_tests(repo_url: str, test_command: str = "npm test", branch: str = "main") -> dict:
    test_cmd = f"""
cd /tmp && git clone --depth 1 -b {branch} {repo_url} repo && cd repo && \
{test_command}
"""
    return await execute_in_sandbox(test_cmd, timeout=300)

async def apply_patch_and_test(
    repo_url: str,
    patch_content: str,
    test_command: str = "npm test",
    branch: str = "main",
) -> dict:
    patch_b64 = __import__('base64').b64encode(patch_content.encode()).decode()
    cmd = f"""
cd /tmp && git clone --depth 1 -b {branch} {repo_url} repo && cd repo && \
echo "{patch_b64}" | base64 -d > /tmp/patch.diff && \
git apply /tmp/patch.diff && \
{test_command}
"""
    return await execute_in_sandbox(cmd, timeout=300)

import asyncio
