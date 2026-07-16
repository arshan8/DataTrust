from fastapi import APIRouter, Depends, Header, HTTPException
from app.core.security import get_current_user_id
from app.services.authz_service import get_user_context
from app.services.vector_retrieval_service import retrieve_authorized_chunks

router = APIRouter()

@router.post("/debug/retrieve")
def debug_retrieve(payload: dict, user_id: str = Depends(get_current_user_id)):
    user_context = get_user_context(user_id)
    query = payload.get("text", "")
    result = retrieve_authorized_chunks(query, user_context, top_k=payload.get("top_k", 5))
    return result

from app.core.security import verify_auth0_token

@router.get("/auth/debug/login")
def auth_debug(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")

    token = authorization.replace("Bearer ", "").strip()
    payload = verify_auth0_token(token)

    return {
        "sub": payload.get("sub"),
        "email": payload.get("email"),
        "aud": payload.get("aud"),
        "iss": payload.get("iss"),
        "scope": payload.get("scope"),
    }