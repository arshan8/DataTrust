import logging
from typing import Any

from app.db.supabase_client import supabase

logger = logging.getLogger(__name__)


def get_allowed_resource_scopes(user_context: dict) -> list[dict]:
    department = user_context["department"]
    auth_rank = user_context["auth_rank"]

    result = (
        supabase.table("resource_scopes")
        .select("""
            id,
            resource_type,
            external_resource_id,
            parent_resource_id,
            resource_name,
            resource_path,
            is_active,
            metadata,
            source_systems:source_system_id(code,name),
            departments:department_id(code,name),
            auth_levels:min_auth_level_id(code,rank)
        """)
        .eq("is_active", True)
        .execute()
    )

    scopes = []
    seen = set()

    for row in result.data or []:
        row_department = row["departments"]["code"] if row.get("departments") else None
        min_rank = row["auth_levels"]["rank"] if row.get("auth_levels") else 999

        if row_department != department:
            continue

        if auth_rank < min_rank:
            continue

        key = (
            row["source_systems"]["code"],
            row["external_resource_id"],
            row.get("parent_resource_id"),
            row.get("resource_path"),
            row_department,
            min_rank,
        )

        if key in seen:
            continue

        seen.add(key)

        scopes.append({
            "scope_id": row["id"],
            "source_type": row["source_systems"]["code"],
            "source_name": row["source_systems"]["name"],
            "resource_type": row["resource_type"],
            "external_resource_id": row["external_resource_id"],
            "parent_resource_id": row.get("parent_resource_id"),
            "resource_name": row["resource_name"],
            "resource_path": row["resource_path"],
            "department": row["departments"]["code"],
            "department_name": row["departments"]["name"],
            "min_auth_level": row["auth_levels"]["code"],
            "min_auth_rank": min_rank,
            "metadata": row.get("metadata", {}),
        })

    return scopes