from fastapi import HTTPException
from app.services.authz_service import get_user_context


def require_admin_user(user_id: str) -> dict:
    user_context = get_user_context(user_id)

    if not user_context.get("is_active"):
        raise HTTPException(status_code=403, detail="Inactive user")

    if not user_context.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin access required")

    return user_context