from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user_id
from app.services.authz_service import get_user_context
from app.db.supabase_client import supabase
from app.db.mongodb_client import get_mongo_db
from datetime import datetime
from collections import defaultdict
from app.services.admin_auth_service import require_admin_user

router = APIRouter()


def require_admin(user_id: str):
    user = get_user_context(user_id)
    if not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/admin/summary")
def admin_summary(user_id: str = Depends(get_current_user_id)):
    require_admin(user_id)

    docs = supabase.table("documents").select("id,is_active").execute().data or []
    chunks = supabase.table("document_chunks").select("id,is_active").execute().data or []
    users = supabase.table("app_users").select("id,is_active,is_admin").execute().data or []

    return {
        "total_documents": len(docs),
        "active_documents": len([d for d in docs if d.get("is_active")]),
        "total_chunks": len(chunks),
        "active_chunks": len([c for c in chunks if c.get("is_active")]),
        "total_users": len(users),
        "active_users": len([u for u in users if u.get("is_active")]),
        "admin_users": len([u for u in users if u.get("is_admin")]),
    }


@router.get("/admin/documents-by-source")
def documents_by_source(user_id: str = Depends(get_current_user_id)):
    require_admin(user_id)

    docs = (
        supabase.table("documents")
        .select("id, source_systems(code)")
        .execute()
        .data
        or []
    )

    counts = {}
    for d in docs:
        source = d.get("source_systems", {}).get("code", "UNKNOWN")
        counts[source] = counts.get(source, 0) + 1

    return [{"name": k, "value": v} for k, v in counts.items()]


@router.get("/admin/documents-by-department")
def documents_by_department(user_id: str = Depends(get_current_user_id)):
    require_admin(user_id)

    docs = (
        supabase.table("documents")
        .select("id, departments(code)")
        .execute()
        .data
        or []
    )

    counts = {}
    for d in docs:
        dept = d.get("departments", {}).get("code", "UNKNOWN")
        counts[dept] = counts.get(dept, 0) + 1

    return [{"name": k, "value": v} for k, v in counts.items()]


@router.get("/admin/chunks-by-level")
def chunks_by_level(user_id: str = Depends(get_current_user_id)):
    require_admin(user_id)

    chunks = (
        supabase.table("document_chunks")
        .select("id, auth_levels(code)")
        .eq("is_active", True)
        .execute()
        .data
        or []
    )

    counts = {}
    for c in chunks:
        level = c.get("auth_levels", {}).get("code", "UNKNOWN")
        counts[level] = counts.get(level, 0) + 1

    return [{"name": k, "value": v} for k, v in counts.items()]


# @router.get("/admin/recent-documents")
# def recent_documents(user_id: str = Depends(get_current_user_id)):
#     require_admin(user_id)

#     return (
#         supabase.table("documents")
#         .select(
#             "id,title,resource_path,sync_status,is_active,created_at,updated_at,"
#             "source_systems(code),departments(code),auth_levels(code)"
#         )
#         .order("updated_at", desc=True)
#         .limit(10)
#         .execute()
#         .data
#         or []
#     )
@router.get("/admin/recent-documents")
def recent_documents(user_id: str = Depends(get_current_user_id)):
    require_admin_user(user_id)

    try:
        result = (
            supabase.table("documents")
            .select("""
                id,
                title,
                resource_path,
                sync_status,
                created_at,
                updated_at,
                source_systems:source_system_id(code,name),
                departments:department_id(code,name),
                auth_levels:min_auth_level_id(code,rank)
            """)
            .order("updated_at", desc=True)
            .limit(25)
            .execute()
        )

        return result.data or []

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch recent documents: {str(e)}"
        )


@router.get("/admin/recent-policy-events")
def recent_policy_events(user_id: str = Depends(get_current_user_id)):
    require_admin(user_id)

    try:
        return (
            supabase.table("policy_events")
            .select("*")
            .order("created_at", desc=True)
            .limit(20)
            .execute()
            .data
            or []
        )
    except Exception:
        return []


@router.get("/admin/data-quality")
def admin_data_quality(user_id: str = Depends(get_current_user_id)):
    require_admin(user_id)

    docs = (
        supabase.table("documents")
        .select("id,resource_path,is_active")
        .execute()
        .data
        or []
    )

    chunks = (
        supabase.table("document_chunks")
        .select("id,resource_path,is_active,chunk_text")
        .limit(5000)
        .execute()
        .data
        or []
    )

    local_path_issues = [
        c for c in chunks
        if str(c.get("resource_path", "")).startswith(("/Users/", "/home/"))
    ]

    empty_chunks = [
        c for c in chunks
        if not str(c.get("chunk_text", "")).strip()
    ]

    inactive_chunks = [c for c in chunks if not c.get("is_active")]

    return {
        "document_count": len(docs),
        "chunk_count": len(chunks),
        "local_path_issues": len(local_path_issues),
        "empty_chunks": len(empty_chunks),
        "inactive_chunks": len(inactive_chunks),
        "status": "healthy" if not local_path_issues and not empty_chunks else "needs_attention",
    }


from datetime import datetime, timezone, timedelta
from collections import defaultdict
from app.db.supabase_client import supabase


@router.get("/admin/connector-health")
def connector_health(user_id: str = Depends(get_current_user_id)):
    require_admin(user_id)

    sources = supabase.table("source_systems").select("*").execute().data or []
    docs = supabase.table("documents").select("source_system_id,sync_status,updated_at").execute().data or []

    result = []

    for source in sources:
        source_docs = [d for d in docs if d.get("source_system_id") == source["id"]]
        latest = max([d.get("updated_at") for d in source_docs if d.get("updated_at")], default=None)

        failures = len([d for d in source_docs if d.get("sync_status") in ["failed", "error"]])
        active = len(source_docs)

        result.append({
            "source": source["code"],
            "name": source.get("name"),
            "status": "healthy" if failures == 0 else "attention",
            "document_count": active,
            "failure_count": failures,
            "last_sync_at": latest,
        })

    return result


@router.get("/admin/ingestion-progress")
def ingestion_progress(user_id: str = Depends(get_current_user_id)):
    require_admin(user_id)

    docs = (
        supabase.table("documents")
        .select("id,title,sync_status,updated_at,source_systems(code),departments(code),auth_levels(code)")
        .order("updated_at", desc=True)
        .limit(50)
        .execute()
        .data
        or []
    )

    total = len(docs)
    active = len([d for d in docs if d.get("sync_status") in ["active", "updated", "success"]])
    failed = len([d for d in docs if d.get("sync_status") in ["failed", "error"]])
    no_change = len([d for d in docs if d.get("sync_status") == "no_change"])

    return {
        "total_recent_documents": total,
        "active_or_updated": active,
        "failed": failed,
        "no_change": no_change,
        "recent": docs,
    }


@router.get("/admin/policy-violations-chart")
def policy_violations_chart(user_id: str = Depends(get_current_user_id)):
    require_admin(user_id)

    db = get_mongo_db()

    events = list(
        db.audit_logs.find(
            {},
            {
                "event_type": 1,
                "created_at": 1,
                "payload.result.decision": 1,
                "payload.policy.decision": 1,
                "payload.response.policy.decision": 1,
            },
        )
        .sort("created_at", -1)
        .limit(1000)
    )

    counts = defaultdict(int)

    for e in events:
        event_type = str(e.get("event_type", "")).upper()

        result_decision = (
            e.get("payload", {}).get("result", {}).get("decision")
            or e.get("payload", {}).get("policy", {}).get("decision")
            or e.get("payload", {}).get("response", {}).get("policy", {}).get("decision")
        )

        is_violation = (
            "BLOCK" in event_type
            or "DENIED" in event_type
            or result_decision == "block"
        )

        if not is_violation:
            continue

        created_at = e.get("created_at")
        if isinstance(created_at, datetime):
            day = created_at.strftime("%Y-%m-%d")
        else:
            day = str(created_at)[:10]

        counts[day] += 1

    return [{"date": k, "violations": v} for k, v in sorted(counts.items())]


@router.get("/admin/user-activity-heatmap")
def user_activity_heatmap(user_id: str = Depends(get_current_user_id)):
    require_admin(user_id)

    db = get_mongo_db()

    now = datetime.utcnow().date()
    start = now - timedelta(weeks=6)

    events = list(
        db.audit_logs.find(
            {"created_at": {"$gte": datetime.combine(start, datetime.min.time())}},
            {"created_at": 1},
        )
        .sort("created_at", -1)
        .limit(5000)
    )

    counts = defaultdict(int)

    for e in events:
        created_at = e.get("created_at")
        if not isinstance(created_at, datetime):
            continue

        date_key = created_at.date().strftime("%Y-%m-%d")
        counts[date_key] += 1

    result = []
    current = start

    while current <= now:
        date_key = current.strftime("%Y-%m-%d")
        result.append({
            "date": date_key,
            "day": current.strftime("%a"),
            "week": current.isocalendar().week,
            "count": counts.get(date_key, 0),
        })
        current += timedelta(days=1)

    return result

@router.get("/admin/recent-blocked")
def recent_blocked(user_id: str = Depends(get_current_user_id)):
    require_admin(user_id)

    db = get_mongo_db()

    events = list(
        db.audit_logs.find(
            {
                "$or": [
                    {"event_type": {"$regex": "BLOCK", "$options": "i"}},
                    {"payload.result.decision": "block"},
                    {"payload.policy.decision": "block"},
                    {"payload.response.policy.decision": "block"},
                ]
            }
        )
        .sort("created_at", -1)
        .limit(20)
    )

    output = []

    for e in events:
        payload = e.get("payload", {})

        output.append({
            "id": str(e.get("_id")),
            "event_type": e.get("event_type"),
            "created_at": e.get("created_at").isoformat() if e.get("created_at") else None,
            "query": (
                payload.get("query")
                or payload.get("input", {}).get("original_text")
                or payload.get("response", {}).get("metadata", {}).get("normalized_text")
            ),
            "user_id": payload.get("user_id") or payload.get("user", {}).get("user_id"),
            "department": payload.get("user", {}).get("department"),
            "auth_level": payload.get("user", {}).get("auth_level"),
            "reason": (
                payload.get("policy", {}).get("reason_category")
                or payload.get("result", {}).get("reason_category")
            ),
            "risk_score": (
                payload.get("policy", {}).get("risk_score")
                or payload.get("result", {}).get("risk_score")
            ),
        })

    return output
