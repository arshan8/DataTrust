# app/routers/github_connector.py
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.services.connectors_sources.github_connector import (
    walk_repo_files,
    fetch_github_file_text,
)
from app.services.ingestion_common_service import ingest_text_document

router = APIRouter()


class GithubIngestRequest(BaseModel):
    owner: str | None = None
    repo: str | None = None
    branch: str = "main"
    start_path: str = ""
    source_code: str = "GITHUB"
    department_code: str
    level_code: str
    scope_external_id: str
    max_files: int = 20


@router.post("/ingest/github")
def ingest_github(request: GithubIngestRequest):
    owner = request.owner or settings.GITHUB_OWNER
    repo = request.repo or settings.GITHUB_REPO

    files = walk_repo_files(owner, repo, request.start_path, request.branch)
    files = files[: request.max_files]

    results = []

    for file_item in files:
        path = file_item["path"]
        file_data = fetch_github_file_text(owner, repo, path, request.branch)

        result = ingest_text_document(
            source_code=request.source_code,
            department_code=request.department_code,
            level_code=request.level_code,
            scope_external_id=request.scope_external_id,
            external_doc_id=file_data["external_doc_id"],
            external_parent_id=f"github:{owner}/{repo}",
            title=file_data["title"],
            resource_path=file_data["resource_path"],
            source_url=file_data["source_url"],
            raw_text=file_data["content_text"],
            metadata={
                "connector": "github",
                "owner": owner,
                "repo": repo,
                "branch": request.branch,
                "path": path,
                "sha": file_data["sha"],
            },
        )
        results.append(result)

    return {
        "status": "success",
        "file_count": len(files),
        "results": results,
    }