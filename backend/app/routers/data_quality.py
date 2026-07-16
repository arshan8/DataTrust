# app/routers/data_quality.py
from fastapi import APIRouter
from app.db.supabase_client import supabase

router = APIRouter()


@router.get("/verification/data-quality")
def data_quality():
    docs = supabase.table("documents").select("*").execute().data or []
    chunks = supabase.table("document_chunks").select("*").execute().data or []

    bad_paths = [
        {
            "chunk_id": c.get("id"),
            "document_id": c.get("document_id"),
            "resource_path": c.get("resource_path"),
        }
        for c in chunks
        if str(c.get("resource_path", "")).startswith(("/Users/", "/home/", "C:\\"))
    ]

    inactive_chunks = [c for c in chunks if not c.get("is_active")]
    active_chunks = [c for c in chunks if c.get("is_active")]

    empty_chunks = [
        {
            "chunk_id": c.get("id"),
            "document_id": c.get("document_id"),
        }
        for c in chunks
        if not str(c.get("chunk_text", "")).strip()
    ]

    return {
        "document_count": len(docs),
        "chunk_count": len(chunks),
        "active_chunk_count": len(active_chunks),
        "inactive_chunk_count": len(inactive_chunks),
        "bad_local_paths": bad_paths,
        "empty_chunks": empty_chunks,
    }