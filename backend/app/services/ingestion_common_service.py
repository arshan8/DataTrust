# app/services/ingestion_common_service.py
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


def get_required_ids(source_code: str, department_code: str, level_code: str, scope_external_id: str):
    source_system = supabase.table("source_systems").select("id").eq("code", source_code).single().execute().data
    department = supabase.table("departments").select("id").eq("code", department_code).single().execute().data
    auth_level = supabase.table("auth_levels").select("id").eq("code", level_code).single().execute().data
    scope_rows = (
        supabase.table("resource_scopes")
        .select("id")
        .eq("external_resource_id", scope_external_id)
        .limit(1)
        .execute()
        .data
    )

    if not source_system or not department or not auth_level or not scope_rows:
        raise ValueError("source_system, department, auth_level, or resource_scope not found")

    return source_system["id"], department["id"], auth_level["id"], scope_rows[0]["id"]


def ingest_text_document(
    source_code: str,
    department_code: str,
    level_code: str,
    scope_external_id: str,
    external_doc_id: str,
    external_parent_id: str | None,
    title: str,
    resource_path: str,
    source_url: str | None,
    raw_text: str,
    metadata: dict,
) -> dict:
    source_system_id, department_id, auth_level_id, scope_id = get_required_ids(
        source_code,
        department_code,
        level_code,
        scope_external_id,
    )

    normalized = normalize_text(raw_text)
    content_hash = hash_text(normalized)

    existing_document = get_document_by_source(source_system_id, external_doc_id)

    if existing_document and existing_document.get("content_hash") == content_hash:
        return {
            "document_id": existing_document["id"],
            "external_doc_id": external_doc_id,
            "chunk_count": 0,
            "status": "no_change",
            "content_hash": content_hash,
        }

    document = upsert_document({
        "source_system_id": source_system_id,
        "resource_scope_id": scope_id,
        "external_doc_id": external_doc_id,
        "external_parent_id": external_parent_id,
        "title": title,
        "resource_path": resource_path,
        "source_url": source_url,
        "department_id": department_id,
        "min_auth_level_id": auth_level_id,
        "content_hash": content_hash,
        "content_text": normalized,
        "last_modified_at": datetime.now(timezone.utc).isoformat(),
        "sync_status": "active",
        "is_active": True,
        "metadata": metadata,
    })

    document_id = document["id"]
    deactivate_chunks_for_document(document_id)

    chunks = chunk_text(normalized, chunk_size_words=180, overlap_words=30)
    inserted = 0

    for chunk in chunks:
        embedding = generate_embedding(chunk["chunk_text"])

        upsert_chunk({
            "document_id": document_id,
            "chunk_index": chunk["chunk_index"],
            "chunk_text": chunk["chunk_text"],
            "chunk_hash": chunk["chunk_hash"],
            "token_count": chunk["token_count"],
            "source_system_id": source_system_id,
            "resource_scope_id": scope_id,
            "department_id": department_id,
            "min_auth_level_id": auth_level_id,
            "resource_path": resource_path,
            "is_active": True,
            "metadata": metadata,
            "embedding": embedding,
        })
        inserted += 1

    return {
        "document_id": document_id,
        "external_doc_id": external_doc_id,
        "chunk_count": inserted,
        "status": "updated",
        "content_hash": content_hash,
    }