from datetime import datetime, timezone
from app.db.mongo_client import audit_logs


def log_policy_event(event_type: str, payload: dict):
    audit_logs.insert_one({
        "event_type": event_type,
        "payload": payload,
        "created_at": datetime.now(timezone.utc)
    })