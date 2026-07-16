from datetime import datetime, timezone
from app.db.supabase_client import supabase


def get_document_by_source(source_system_id: int, external_doc_id: str) -> dict | None:
    result = (
        supabase.table("documents")
        .select("*")
        .eq("source_system_id", source_system_id)
        .eq("external_doc_id", external_doc_id)
        .limit(1)
        .execute()
    )
    if result.data:
        return result.data[0]
    return None


def upsert_document(document_payload: dict) -> dict:
    payload = {
        **document_payload,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "last_synced_at": datetime.now(timezone.utc).isoformat(),
    }

    result = (
        supabase.table("documents")
        .upsert(payload, on_conflict="source_system_id,external_doc_id")
        .execute()
    )

    if not result.data:
        raise ValueError("Failed to upsert document")

    return result.data[0]


def deactivate_chunks_for_document(document_id: int):
    supabase.table("document_chunks").update({
        "is_active": False,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("document_id", document_id).execute()


def reactivate_chunks_for_document(document_id: int):
    supabase.table("document_chunks").update({
        "is_active": True,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }).eq("document_id", document_id).execute()


def get_active_chunk_count_for_document(document_id: int) -> int:
    result = (
        supabase.table("document_chunks")
        .select("id", count="exact")
        .eq("document_id", document_id)
        .eq("is_active", True)
        .execute()
    )
    return result.count or 0


def upsert_chunk(chunk_payload: dict):
    payload = {
        **chunk_payload,
        "is_active": True,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    result = (
        supabase.table("document_chunks")
        .upsert(payload, on_conflict="document_id,chunk_index,chunk_hash")
        .execute()
    )

    return result.data[0] if result.data else None