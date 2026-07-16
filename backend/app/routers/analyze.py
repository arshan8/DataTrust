from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from app.core.security import get_current_user_id
from app.models.policy_models import AnalyzeRequest, AnalyzeResponse
from app.services.authz_service import get_user_context
from app.services.policy_service import analyze_text
from app.services.audit_service import log_policy_event
import uuid

router = APIRouter()


@router.post("/analyze", response_model=AnalyzeResponse)
def analyze_prompt(
    request: AnalyzeRequest,
    user_id: str = Depends(get_current_user_id)
):
    request_id = str(uuid.uuid4())

    try:
        user_context = get_user_context(user_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"User context error: {str(e)}")

    policy_result = analyze_text(request.text, user_context)

    log_policy_event(
        event_type="PROMPT_POLICY_ANALYSIS",
        payload={
            "request_id": request_id,
            "user": {
                "user_id": user_context["user_id"],
                "email": user_context["email"],
                "department": user_context["department"],
                "auth_level": user_context["auth_level"],
                "auth_rank": user_context["auth_rank"],
                "is_admin": user_context["is_admin"],
            },
            "input": {
                "original_text": request.text,
            },
            "result": policy_result,
        }
    )

    response_payload = {
        "user": {
            "user_id": user_context["user_id"],
            "department": user_context["department"],
            "auth_level": user_context["auth_level"],
        },
        "policy_result": {
            "status": policy_result["status"],
            "decision": policy_result["decision"],
            "risk_level": policy_result["risk_level"],
            "risk_score": policy_result["risk_score"],
            "matched_rules": policy_result["matched_rules"],
            "pii_hits": policy_result["pii_hits"],
            "keyword_hits": policy_result["keyword_hits"],
            "redacted_text": policy_result["redacted_text"],
            "code": policy_result["code"],
            "reason_category": policy_result["reason_category"],
            "user_safe_explanation": policy_result["user_safe_explanation"],
            "suggested_safe_alternative": policy_result["suggested_safe_alternative"],
        }
    }

    if policy_result["status"] == "blocked":
        return JSONResponse(status_code=403, content=response_payload)

    return response_payload