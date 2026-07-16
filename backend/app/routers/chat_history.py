from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Any

from app.core.security import get_current_user_id
from app.services.authz_service import get_user_context
from app.db.mongodb_client import get_mongo_db

router = APIRouter()

class ChatSessionPayload(BaseModel):
    id: str
    title: str = "New chat"
    messages: list[dict[str, Any]] = Field(default_factory=list)
    createdAt: str
    updatedAt: str


def chat_collection():
    mongo_db = get_mongo_db()
    return mongo_db["chat_sessions"]


@router.get("/chat/history")
def list_chat_history(user_id: str = Depends(get_current_user_id)):
    try:
        sessions = list(
            chat_collection()
            .find({"user_id": user_id}, {"_id": 0})
            .sort("updatedAt", -1)
        )

        return {"sessions": sessions}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load chat history: {str(e)}")


@router.post("/chat/history")
def create_chat_history(
    payload: ChatSessionPayload,
    user_id: str = Depends(get_current_user_id),
):
    try:
        user_context = get_user_context(user_id)
        now = datetime.now(timezone.utc).isoformat()

        doc = payload.model_dump()
        doc["user_id"] = user_id
        doc["email"] = user_context.get("email")
        doc["department"] = user_context.get("department")
        doc["auth_level"] = user_context.get("auth_level")
        doc["created_at"] = now
        doc["updated_at"] = now

        chat_collection().update_one(
            {"id": payload.id, "user_id": user_id},
            {"$set": doc},
            upsert=True,
        )

        return {"status": "saved", "id": payload.id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save chat history: {str(e)}")


@router.put("/chat/history/{conversation_id}")
def update_chat_history(
    conversation_id: str,
    payload: ChatSessionPayload,
    user_id: str = Depends(get_current_user_id),
):
    try:
        existing = chat_collection().find_one(
            {"id": conversation_id, "user_id": user_id},
            {"_id": 0},
        )

        now = datetime.now(timezone.utc).isoformat()
        doc = payload.model_dump()
        doc["id"] = conversation_id
        doc["user_id"] = user_id
        doc["updated_at"] = now

        if not existing:
            user_context = get_user_context(user_id)
            doc["email"] = user_context.get("email")
            doc["department"] = user_context.get("department")
            doc["auth_level"] = user_context.get("auth_level")
            doc["created_at"] = doc.get("createdAt") or now
        else:
            doc["email"] = existing.get("email")
            doc["department"] = existing.get("department")
            doc["auth_level"] = existing.get("auth_level")
            doc["created_at"] = existing.get("created_at", now)

        chat_collection().update_one(
            {"id": conversation_id, "user_id": user_id},
            {"$set": doc},
            upsert=True,
        )

        return {"status": "updated", "id": conversation_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update chat history: {str(e)}")


@router.delete("/chat/history/{conversation_id}")
def delete_chat_history(
    conversation_id: str,
    user_id: str = Depends(get_current_user_id),
):
    try:
        chat_collection().delete_one({"id": conversation_id, "user_id": user_id})
        return {"status": "deleted", "id": conversation_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete chat history: {str(e)}")
    

# from datetime import datetime, timezone
# from fastapi import APIRouter, Depends, HTTPException
# from pydantic import BaseModel
# from app.core.security import get_current_user_id
# from app.services.authz_service import get_user_context
# from app.db.mongodb_client import get_mongo_db

# router = APIRouter()
# db = get_mongo_db()

# class ChatSessionPayload(BaseModel):
#     id: str
#     title: str
#     messages: list
#     createdAt: str
#     updatedAt: str


# @router.get("/chat/history")
# def list_chat_history(user_id: str = Depends(get_current_user_id)):
#     sessions = list(
#         db.chat_sessions.find(
#             {"user_id": user_id},
#             {"_id": 0}
#         ).sort("updatedAt", -1)
#     )
#     return {"sessions": sessions}


# @router.post("/chat/history")
# def create_chat_history(
#     payload: ChatSessionPayload,
#     user_id: str = Depends(get_current_user_id),
# ):
#     user_context = get_user_context(user_id)

#     doc = payload.model_dump()
#     doc["user_id"] = user_id
#     doc["email"] = user_context.get("email")
#     doc["department"] = user_context.get("department")
#     doc["auth_level"] = user_context.get("auth_level")
#     doc["created_at"] = datetime.now(timezone.utc).isoformat()
#     doc["updated_at"] = datetime.now(timezone.utc).isoformat()

#     db.chat_sessions.update_one(
#         {"id": payload.id, "user_id": user_id},
#         {"$set": doc},
#         upsert=True,
#     )

#     return {"status": "saved", "id": payload.id}


# @router.put("/chat/history/{conversation_id}")
# def update_chat_history(
#     conversation_id: str,
#     payload: ChatSessionPayload,
#     user_id: str = Depends(get_current_user_id),
# ):
#     doc = payload.model_dump()
#     doc["user_id"] = user_id
#     doc["updated_at"] = datetime.now(timezone.utc).isoformat()

#     result = db.chat_sessions.update_one(
#         {"id": conversation_id, "user_id": user_id},
#         {"$set": doc},
#         upsert=True,
#     )

#     return {"status": "updated", "id": conversation_id}


# @router.delete("/chat/history/{conversation_id}")
# def delete_chat_history(
#     conversation_id: str,
#     user_id: str = Depends(get_current_user_id),
# ):
#     db.chat_sessions.delete_one({"id": conversation_id, "user_id": user_id})
#     return {"status": "deleted", "id": conversation_id}