import base64
import requests
from app.core.config import settings
from app.config.source_manifest import classify_github_path


def _headers():
    return {
        "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }


def list_repo_tree() -> list[dict]:
    url = (
        f"https://api.github.com/repos/{settings.GITHUB_OWNER}/"
        f"{settings.GITHUB_REPO}/git/trees/{settings.GITHUB_BRANCH}?recursive=1"
    )

    res = requests.get(url, headers=_headers(), timeout=60)
    res.raise_for_status()

    return res.json().get("tree", [])


def get_file_text(path: str) -> str:
    url = (
        f"https://api.github.com/repos/{settings.GITHUB_OWNER}/"
        f"{settings.GITHUB_REPO}/contents/{path}"
    )

    res = requests.get(
        url,
        headers=_headers(),
        params={"ref": settings.GITHUB_BRANCH},
        timeout=60,
    )
    res.raise_for_status()

    data = res.json()

    if data.get("encoding") != "base64":
        return ""

    raw = base64.b64decode(data.get("content", "")).decode("utf-8", errors="ignore")
    return raw


def get_ingestable_github_files() -> list[dict]:
    tree = list_repo_tree()
    files = []

    for item in tree:
        if item.get("type") != "blob":
            continue

        path = item.get("path", "")
        mapping = classify_github_path(path)

        if not mapping:
            continue

        department_code, level_code, scope_external_id = mapping

        files.append({
            "path": path,
            "sha": item.get("sha"),
            "size": item.get("size"),
            "department_code": department_code,
            "level_code": level_code,
            "scope_external_id": scope_external_id,
        })

    return files