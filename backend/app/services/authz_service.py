import logging
from app.db.supabase_client import supabase

logger = logging.getLogger(__name__)

def get_user_context(user_id: str) -> dict:
    result = (
        supabase.table("app_users")
        .select("""
            id,
            email,
            full_name,
            is_admin,
            is_active,
            department_id,
            auth_level_id,
            departments:department_id(id,code,name),
            auth_levels:auth_level_id(id,code,rank)
        """)
        .eq("id", user_id)
        .single()
        .execute()
    )

    data = result.data
    if not data:
        logger.error("USER_NOT_FOUND user_id=%s", user_id)
        raise ValueError("User not found in app_users")

    logger.info("USER_CONTEXT_RESOLVED user_context")

    return {
        "user_id": data["id"],
        "email": data["email"],
        "full_name": data.get("full_name"),
        "is_admin": data.get("is_admin", False),
        "is_active": data.get("is_active", False),
        "department_id": data["departments"]["id"] if data.get("departments") else None,
        "department": data["departments"]["code"] if data.get("departments") else None,
        "department_name": data["departments"]["name"] if data.get("departments") else None,
        "auth_level_id": data["auth_levels"]["id"] if data.get("auth_levels") else None,
        "auth_level": data["auth_levels"]["code"] if data.get("auth_levels") else None,
        "auth_rank": data["auth_levels"]["rank"] if data.get("auth_levels") else 0,
    }