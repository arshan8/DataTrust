import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.security import get_current_user_id
from app.services.authz_service import get_user_context
from app.services.orchestrator_service import build_retrieval_plan
from app.services.audit_service import log_policy_event
from app.services.policy_service import analyze_text

logger = logging.getLogger(__name__)
router = APIRouter()


class RetrievalPlanRequest(BaseModel):
    text: str = Field(..., min_length=1)


@router.post("/retrieval-plan")
def retrieval_plan(
    request: RetrievalPlanRequest,
    user_id: str = Depends(get_current_user_id)
):
    logger.info("RETRIEVAL_ROUTE_START user_id=%s text=%r", user_id, request.text)

    try:
        user_context = get_user_context(user_id)
    except Exception as e:
        logger.exception("USER_CONTEXT_ERROR user_id=%s error=%s", user_id, str(e))
        raise HTTPException(status_code=404, detail=f"User context error: {str(e)}")

    logger.info("USER_CONTEXT_RESOLVED user_context=%s", user_context)

    policy_result = analyze_text(request.text, user_context)

    logger.info("RETRIEVAL_POLICY_RESULT user_id=%s policy_result=%s", user_id, policy_result)

    log_policy_event(
        event_type="RETRIEVAL_POLICY_CHECK",
        payload={
            "user_id": user_context["user_id"],
            "department": user_context["department"],
            "auth_level": user_context["auth_level"],
            "query": request.text,
            "policy_decision": policy_result["decision"],
            "risk_level": policy_result["risk_level"],
            "risk_score": policy_result["risk_score"],
            "matched_rules": policy_result["matched_rules"],
        }
    )

    if policy_result["decision"] == "block":
        return {
            "query": request.text,
            "status": "blocked",
            "reason": "Request blocked by policy engine.",
            "policy_result": policy_result,
            "user_context": {
                "user_id": user_context["user_id"],
                "department": user_context["department"],
                "auth_level": user_context["auth_level"],
                "auth_rank": user_context["auth_rank"],
            },
            "selected_sources": [],
            "allowed_scope_count": 0,
            "allowed_scopes": [],
            "source_plan_count": 0,
            "source_plans": [],
        }

    if policy_result["decision"] == "review":
        return {
            "query": request.text,
            "status": "needs_review",
            "reason": "Request requires manual review before retrieval.",
            "policy_result": policy_result,
            "user_context": {
                "user_id": user_context["user_id"],
                "department": user_context["department"],
                "auth_level": user_context["auth_level"],
                "auth_rank": user_context["auth_rank"],
            },
            "selected_sources": [],
            "allowed_scope_count": 0,
            "allowed_scopes": [],
            "source_plan_count": 0,
            "source_plans": [],
        }

    sanitized_query = (
        policy_result["redacted_text"]
        if policy_result["decision"] == "redact"
        else request.text
    )

    plan = build_retrieval_plan(sanitized_query, user_context)

    log_policy_event(
        event_type="RETRIEVAL_PLAN_CREATED",
        payload={
            "user_id": user_context["user_id"],
            "department": user_context["department"],
            "auth_level": user_context["auth_level"],
            "query": request.text,
            "sanitized_query": sanitized_query,
            "selected_sources": plan["selected_sources"],
            "allowed_scope_count": plan["allowed_scope_count"],
            "source_plan_count": plan["source_plan_count"],
            "policy_decision": policy_result["decision"],
        }
    )

    return {
        **plan,
        "status": "planned",
        "policy_result": policy_result,
    }