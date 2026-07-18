from pathlib import Path
from app.services.ingestion_common_service import ingest_text_document
from app.services.sync_service import log_sync_event

SOURCE_MAP = {
    "CONFLUENCE": "CONFLUENCE",
    "GITHUB": "GITHUB",
    "GDRIVE": "GDRIVE",
}


def ingest_local_file(
    file_path: str,
    source_code: str,
    department_code: str,
    level_code: str,
    resource_scope_external_id: str,
) -> dict:
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"File not found: {file_path}")

    raw_text = path.read_text(encoding="utf-8")
    
    external_doc_id = f"{source_code}:{path.name}:{resource_scope_external_id}"
 
    result = ingest_text_document(
        source_code=source_code,
        department_code=department_code,
        level_code=level_code,
        scope_external_id=resource_scope_external_id,
        external_doc_id=external_doc_id,
        external_parent_id=resource_scope_external_id,
        title=path.name,
        resource_path=f"demo://{department_code}/{level_code}/{path.name}",
        source_url=None,
        raw_text=raw_text,
        metadata={
            "source_kind": "local_demo_file",
            "filename": path.name
        }
    )
    
    document_id = result["document_id"]
    inserted_count = result["chunk_count"]

    log_sync_event("LOCAL_FILE_INGESTED", {
        "file_path": str(path),
        "source_code": source_code,
        "department_code": department_code,
        "level_code": level_code,
        "resource_scope_external_id": resource_scope_external_id,
        "document_id": document_id,
        "chunk_count": inserted_count,
    })

    return {
        "document_id": document_id,
        "external_doc_id": external_doc_id,
        "chunk_count": inserted_count,
        "status": "updated" if inserted_count > 0 else "no_change",
    }