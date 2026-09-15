import httpx
from .config import settings

GITHUB_API = "https://api.github.com"

async def get_headers() -> dict:
    return {
        "Authorization": f"token {settings.github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

async def get_repo(owner: str, repo: str) -> dict:
    async with httpx.AsyncClient() as client:
        headers = await get_headers()
        resp = await client.get(f"{GITHUB_API}/repos/{owner}/{repo}", headers=headers)
        resp.raise_for_status()
        return resp.json()

async def get_recent_commits(owner: str, repo: str, branch: str = "main", limit: int = 10) -> list[dict]:
    async with httpx.AsyncClient() as client:
        headers = await get_headers()
        resp = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/commits",
            headers=headers,
            params={"sha": branch, "per_page": limit},
        )
        resp.raise_for_status()
        return resp.json()

async def get_file_tree(owner: str, repo: str, branch: str = "main") -> dict:
    async with httpx.AsyncClient() as client:
        headers = await get_headers()
        resp = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1",
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json()

async def get_file_content(owner: str, repo: str, path: str, branch: str = "main") -> str | None:
    async with httpx.AsyncClient() as client:
        headers = await get_headers()
        resp = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/contents/{path}?ref={branch}",
            headers=headers,
        )
        if resp.status_code != 200:
            return None
        import base64
        data = resp.json()
        return base64.b64decode(data["content"]).decode("utf-8")

async def get_pr(owner: str, repo: str, pr_number: int) -> dict:
    async with httpx.AsyncClient() as client:
        headers = await get_headers()
        resp = await client.get(f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}", headers=headers)
        resp.raise_for_status()
        return resp.json()

async def get_pr_files(owner: str, repo: str, pr_number: int) -> list[dict]:
    async with httpx.AsyncClient() as client:
        headers = await get_headers()
        resp = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/pulls/{pr_number}/files",
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json()

async def get_languages(owner: str, repo: str) -> dict:
    async with httpx.AsyncClient() as client:
        headers = await get_headers()
        resp = await client.get(f"{GITHUB_API}/repos/{owner}/{repo}/languages", headers=headers)
        resp.raise_for_status()
        return resp.json()

async def get_repo_analysis(owner: str, repo: str) -> dict:
    repo_data = await get_repo(owner, repo)
    languages = await get_languages(owner, repo)
    commits = await get_recent_commits(owner, repo, repo_data.get("default_branch", "main"), limit=20)
    tree = await get_file_tree(owner, repo, repo_data.get("default_branch", "main"))

    files = [t["path"] for t in tree.get("tree", []) if t["type"] == "blob"]
    dirs = list(set(t["path"].split("/")[0] for t in tree.get("tree", []) if "/" in t["path"]))

    return {
        "name": repo_data["name"],
        "full_name": repo_data["full_name"],
        "url": repo_data["html_url"],
        "description": repo_data.get("description", ""),
        "default_branch": repo_data.get("default_branch", "main"),
        "languages": languages,
        "file_count": len(files),
        "directories": sorted(dirs),
        "files": files[:200],
        "recent_commits": [
            {
                "sha": c["sha"][:8],
                "message": c["commit"]["message"].split("\n")[0],
                "author": c["commit"]["author"]["name"],
                "date": c["commit"]["author"]["date"],
            }
            for c in commits
        ],
    }
