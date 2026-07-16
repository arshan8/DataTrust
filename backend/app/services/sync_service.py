from datetime import datetime, timezone
from app.db.supabase_client import supabase
from app.db.mongo_client import system_events


def log_sync_event(event_type: str, payload: dict):
    system_events.insert_one({
        "event_type": event_type,
        "payload": payload,
        "created_at": datetime.now(timezone.utc)
    })


def upsert_connector_sync_state(payload: dict):
    payload["last_synced_at"] = datetime.now(timezone.utc).isoformat()

    result = (
        supabase.table("connector_sync_state")
        .upsert(payload, on_conflict="source_system_id,external_doc_id")
        .execute()
    )
    return result.data[0] if result.data else None