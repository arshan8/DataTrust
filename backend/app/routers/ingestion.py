from fastapi import APIRouter, Depends, HTTPException
from app.core.security import get_current_user_id
from app.services.authz_service import get_user_context
from app.services.github_ingestion_service import ingest_mock_github_document


router = APIRouter()


@router.post("/ingest/mock-github")
def ingest_mock_github(user_id: str = Depends(get_current_user_id)):
    user_context = get_user_context(user_id)

    if user_context["department"] != "TECH" or user_context["auth_rank"] < 2:
        raise HTTPException(status_code=403, detail="Not authorized to run mock GitHub ingestion")

    try:
        result = ingest_mock_github_document(user_context)
        return {
            "status": "success",
            "message": "Mock GitHub ingestion completed",
            "result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))