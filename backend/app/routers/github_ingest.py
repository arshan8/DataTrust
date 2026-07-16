from fastapi import APIRouter
from app.core.config import settings
from app.services.connectors_sources.github_connector import (
    get_ingestable_github_files,
    get_file_text,
)
from app.services.ingestion_common_service import ingest_text_document

router = APIRouter()


@router.get("/debug/github-files")
def debug_github_files():
    files = get_ingestable_github_files()
    return {
        "count": len(files),
        "files": files,
    }


@router.post("/ingest/github")
def ingest_github():
    files = get_ingestable_github_files()

    results = []
    skipped = []
    failed = []

    for f in files:
        path = f["path"]

        try:
            raw_text = get_file_text(path)

            if not raw_text.strip():
                skipped.append({"path": path, "reason": "empty_file"})
                continue

            result = ingest_text_document(
                source_code="GITHUB",
                department_code=f["department_code"],
                level_code=f["level_code"],
                scope_external_id=f["scope_external_id"],
                external_doc_id=f"github:{settings.GITHUB_OWNER}/{settings.GITHUB_REPO}/{path}",
                external_parent_id=settings.GITHUB_REPO,
                title=path.split("/")[-1],
                resource_path=f"github://{settings.GITHUB_OWNER}/{settings.GITHUB_REPO}/{path}",
                source_url=f"https://github.com/{settings.GITHUB_OWNER}/{settings.GITHUB_REPO}/blob/{settings.GITHUB_BRANCH}/{path}",
                raw_text=raw_text,
                metadata={
                    "connector": "github",
                    "repo": settings.GITHUB_REPO,
                    "branch": settings.GITHUB_BRANCH,
                    "path": path,
                    "sha": f.get("sha"),
                    "size": f.get("size"),
                },
            )

            results.append(result)

        except Exception as e:
            failed.append({
                "path": path,
                "error": str(e),
            })

    return {
        "status": "completed_with_errors" if failed else "success",
        "ingested_count": len(results),
        "skipped_count": len(skipped),
        "failed_count": len(failed),
        "results": results,
        "skipped": skipped,
        "failed": failed,
    }