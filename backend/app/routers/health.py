from fastapi import APIRouter
from app.db.mongo_client import mongo_db
from app.db.supabase_client import supabase

router = APIRouter()

@router.get("/health")
def health():
    mongo_ok = False
    supabase_ok = False

    try:
        mongo_db.command("ping")
        mongo_ok = True
    except Exception:
        mongo_ok = False

    try:
        supabase.table("departments").select("id").limit(1).execute()
        supabase_ok = True
    except Exception:
        supabase_ok = False

    return {
        "status": "ok",
        "mongodb": mongo_ok,
        "supabase": supabase_ok
    }