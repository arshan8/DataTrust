from pathlib import Path
from datetime import datetime, timezone

from app.db.supabase_client import supabase
from app.services.chunking_service import normalize_text, hash_text, chunk_text
from app.services.embedding_service import generate_embedding
from app.services.document_service import (
    get_document_by_source,
    upsert_document,
    deactivate_chunks_for_document,
    upsert_chunk,
)
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
    normalized = normalize_text(raw_text)
    content_hash = hash_text(normalized)

    source_system = supabase.table("source_systems").select("id").eq("code", source_code).single().execute().data
    department = supabase.table("departments").select("id").eq("code", department_code).single().execute().data
    auth_level = supabase.table("auth_levels").select("id").eq("code", level_code).single().execute().data

    scope_rows = (
        supabase.table("resource_scopes")
        .select("id")
        .eq("external_resource_id", resource_scope_external_id)
        .limit(1)
        .execute()
        .data
    )

    if not source_system or not department or not auth_level or not scope_rows:
        raise ValueError("Required source system / department / auth level / scope not found")

    external_doc_id = f"{source_code}:{path.name}:{resource_scope_external_id}"
    existing_document = get_document_by_source(source_system["id"], external_doc_id)

    document = upsert_document({
        "source_system_id": source_system["id"],
        "resource_scope_id": scope_rows[0]["id"],
        "external_doc_id": external_doc_id,
        "external_parent_id": resource_scope_external_id,
        "title": path.name,
        "resource_path": f"demo://{department_code}/{level_code}/{path.name}",
        "source_url": None,
        "department_id": department["id"],
        "min_auth_level_id": auth_level["id"],
        "content_hash": content_hash,
        "content_text": normalized,
        "last_modified_at": datetime.now(timezone.utc).isoformat(),
        "sync_status": "active",
        "is_active": True,
        "metadata": {
            "source_kind": "local_demo_file",
            "filename": path.name
        }
    })

    document_id = document["id"]

    if not existing_document or existing_document.get("content_hash") != content_hash:
        deactivate_chunks_for_document(document_id)

        chunks = chunk_text(normalized, chunk_size_words=180, overlap_words=30)

        inserted_count = 0
        for chunk in chunks:
            embedding = generate_embedding(chunk["chunk_text"])

            upsert_chunk({
                "document_id": document_id,
                "chunk_index": chunk["chunk_index"],
                "chunk_text": chunk["chunk_text"],
                "chunk_hash": chunk["chunk_hash"],
                "token_count": chunk["token_count"],
                "source_system_id": source_system["id"],
                "resource_scope_id": scope_rows[0]["id"],
                "department_id": department["id"],
                "min_auth_level_id": auth_level["id"],
                "is_active": True,
                "resource_path": f"demo://{department_code}/{level_code}/{path.name}",
                "metadata": {
                    "filename": path.name
                },
                "embedding": embedding,
            })
            inserted_count += 1
    else:
        inserted_count = 0

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