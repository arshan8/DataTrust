from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.core.security import get_current_user_id
from app.services.authz_service import get_user_context
from app.db.supabase_client import supabase

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/login")
def login(body: LoginRequest):
    try:
        response = supabase.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not response.user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    auth_user_id = response.user.id

    # Look up the app_users record linked to this auth user
    result = (
        supabase.table("app_users")
        .select("id")
        .eq("id", auth_user_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=403, detail="User not registered in the system")

    return {"user_id": result.data["id"]}


@router.get("/me")
def me(user_id: str = Depends(get_current_user_id)):
    try:
        return get_user_context(user_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))