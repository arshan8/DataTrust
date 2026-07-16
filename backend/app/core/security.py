# from fastapi import Header, HTTPException

# def get_current_user_id(x_user_id: str = Header(default=None)) -> str:
#     if not x_user_id:
#         raise HTTPException(status_code=401, detail="Missing X-User-Id header")
#     return x_user_id

import requests
from jose import jwt
from fastapi import Header, HTTPException
from app.core.config import settings
from app.db.supabase_client import supabase

_jwks_cache = None


def _get_jwks():
    global _jwks_cache

    if _jwks_cache is not None:
        return _jwks_cache

    if not settings.AUTH0_DOMAIN:
        raise HTTPException(status_code=500, detail="AUTH0_DOMAIN not configured")

    url = f"https://{settings.AUTH0_DOMAIN}/.well-known/jwks.json"
    res = requests.get(url, timeout=10)
    res.raise_for_status()

    _jwks_cache = res.json()
    return _jwks_cache


def verify_auth0_token(token: str) -> dict:
    try:
        jwks = _get_jwks()
        unverified_header = jwt.get_unverified_header(token)

        rsa_key = None
        for key in jwks["keys"]:
            if key["kid"] == unverified_header["kid"]:
                rsa_key = key
                break

        if rsa_key is None:
            raise HTTPException(status_code=401, detail="Invalid token key")

        payload = jwt.decode(
            token,
            rsa_key,
            algorithms=["RS256"],
            audience=settings.AUTH0_AUDIENCE,
            issuer=settings.AUTH0_ISSUER,
        )

        return payload

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid Auth0 token: {str(e)}")


def map_auth0_subject_to_app_user_id(subject: str) -> str:
    result = (
        supabase.table("auth_identity_map")
        .select("app_user_id,is_active")
        .eq("external_subject", subject)
        .eq("is_active", True)
        .limit(1)
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=403,
            detail="Authenticated Auth0 user is not mapped to a DataTrust user",
        )

    return result.data[0]["app_user_id"]


def get_current_user_id(
    authorization: str | None = Header(default=None),
    x_user_id: str | None = Header(default=None),
) -> str:
    """
    Priority:
    1. Auth0 Bearer token for real app.
    2. X-User-Id fallback for /demo and development.
    """

    if authorization and authorization.startswith("Bearer "):
        token = authorization.replace("Bearer ", "").strip()
        payload = verify_auth0_token(token)
        subject = payload.get("sub")

        if not subject:
            raise HTTPException(status_code=401, detail="Auth0 token missing subject")

        return map_auth0_subject_to_app_user_id(subject)

    if x_user_id:
        return x_user_id

    raise HTTPException(status_code=401, detail="Missing authentication")