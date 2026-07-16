from fastapi import APIRouter
from app.db.supabase_client import supabase

router = APIRouter()


@router.get("/verification/documents")
def list_documents():
    result = (
        supabase.table("documents")
        .select("""
            id,
            external_doc_id,
            title,
            resource_path,
            content_hash,
            sync_status,
            is_active,
            departments:department_id(code,name),
            auth_levels:min_auth_level_id(code,rank)
        """)
        .order("id", desc=True)
        .limit(20)
        .execute()
    )
    return result.data


@router.get("/verification/chunks")
def list_chunks(active_only: bool = False):
    query = (
        supabase.table("document_chunks")
        .select("""
            id,
            document_id,
            chunk_index,
            chunk_text,
            chunk_hash,
            token_count,
            resource_path,
            is_active
        """)
        .order("id", desc=True)
        .limit(50)
    )

    if active_only:
        query = query.eq("is_active", True)

    result = query.execute()
    return result.data


@router.get("/verification/sync-state")
def list_sync_state():
    result = (
        supabase.table("connector_sync_state")
        .select("*")
        .order("id", desc=True)
        .limit(20)
        .execute()
    )
    return result.data