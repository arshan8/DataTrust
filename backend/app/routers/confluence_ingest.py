from fastapi import APIRouter
from pydantic import BaseModel

from app.config.source_manifest import CONFLUENCE_PAGE_ACCESS
from app.services.connectors_sources.confluence_connector import list_pages, get_page_with_body
from app.services.ingestion_common_service import ingest_text_document

router = APIRouter()


class ConfluenceIngestRequest(BaseModel):
    space_key: str = "BC"
    max_pages: int = 100


@router.get("/debug/confluence-pages")
def debug_confluence_pages(space_key: str = "BC"):
    pages = list_pages(space_key=space_key, limit=50)
    return [
        {
            "id": p.get("id"),
            "title": p.get("title"),
            "webui": p.get("_links", {}).get("webui"),
            "mapped": p.get("title") in CONFLUENCE_PAGE_ACCESS,
            "mapping": CONFLUENCE_PAGE_ACCESS.get(p.get("title")),
        }
        for p in pages
    ]


@router.post("/ingest/confluence")
def ingest_confluence(request: ConfluenceIngestRequest):
    pages = list_pages(space_key=request.space_key, limit=50)[: request.max_pages]

    results = []
    skipped = []
    failed = []

    for page in pages:
        title = page.get("title")

        if title not in CONFLUENCE_PAGE_ACCESS:
            skipped.append({
                "id": page.get("id"),
                "title": title,
                "reason": "not_in_manifest"
            })
            continue

        try:
            department_code, level_code, scope_external_id = CONFLUENCE_PAGE_ACCESS[title]
            body = get_page_with_body(page["id"])

            result = ingest_text_document(
                source_code="CONFLUENCE",
                department_code=department_code,
                level_code=level_code,
                scope_external_id=scope_external_id,
                external_doc_id=f"confluence:{body['id']}",
                external_parent_id=f"confluence-space:{request.space_key}",
                title=body["title"],
                resource_path=body["resource_path"],
                source_url=body["source_url"],
                raw_text=body["content_text"],
                metadata={
                    "connector": "confluence",
                    "space_key": request.space_key,
                    "page_id": body["id"],
                    "version": body["version"],
                    "department": department_code,
                    "min_level": level_code,
                    "scope_external_id": scope_external_id,
                },
            )
            results.append(result)

        except Exception as e:
            failed.append({
                "id": page.get("id"),
                "title": title,
                "error": str(e),
                "mapping": CONFLUENCE_PAGE_ACCESS.get(title),
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