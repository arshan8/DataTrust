import json
import time
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse

from app.core.security import get_current_user_id
from app.models.chat_models import ChatRequest
from app.services.authz_service import get_user_context
from app.services.request_understanding_service import understand_request
from app.services.policy_service import analyze_text
from app.services.vector_retrieval_service import retrieve_authorized_chunks
from app.services.query_routing_service import decide_query_route
from app.services.generation_service import (
    generate_answer,
    stream_answer,
    generate_general_answer,
    stream_general_answer,
)
from app.services.output_guard_service import validate_generated_answer
from app.services.audit_service import log_policy_event


router = APIRouter()

SMALL_TALK_INPUTS = {
    "hi": "Hello! How can I help you with your authorized internal knowledge today?",
    "hello": "Hello! How can I help you with your authorized internal knowledge today?",
    "hey": "Hi! What internal document, system, or architecture topic would you like help with?",
    "thanks": "You're welcome.",
    "thank you": "You're welcome.",
    "good morning": "Good morning! How can I help you with your internal knowledge today?",
    "good afternoon": "Good afternoon! How can I help you with your internal knowledge today?",
    "good evening": "Good evening! How can I help you with your internal knowledge today?",
}


def build_policy_response(policy_result: dict, understanding: dict):
    return {
        "status": policy_result["status"],
        "decision": policy_result["decision"],
        "code": policy_result.get("code"),
        "reason_category": policy_result.get("reason_category"),
        "user_safe_explanation": policy_result.get("user_safe_explanation"),
        "suggested_safe_alternative": policy_result.get("suggested_safe_alternative"),
        "matched_rules": policy_result["matched_rules"],
        "categories": understanding["categories"],
        "action": understanding["action"],
        "risk_level": policy_result["risk_level"],
        "risk_score": policy_result["risk_score"],
    }


def apply_semantic_policy_overrides(policy_result: dict, understanding: dict):
    categories = understanding["categories"]
    action = understanding["action"]
    normalized_text = understanding["normalized_text"]

    if "PROMPT_INJECTION" in categories:
        policy_result["status"] = "blocked"
        policy_result["decision"] = "block"
        policy_result["code"] = "POLICY_DENIED"
        policy_result["reason_category"] = "PROMPT_INJECTION"
        policy_result["user_safe_explanation"] = (
            "This request appears to attempt policy bypass or hidden instruction access."
        )
        policy_result["suggested_safe_alternative"] = (
            "Ask a scoped question about approved internal resources."
        )
        policy_result["matched_rules"] = list(
            set(policy_result["matched_rules"] + ["PROMPT_INJECTION"])
        )
        policy_result["risk_level"] = "high"
        policy_result["risk_score"] = max(policy_result["risk_score"], 85)

    if "PII_HIGH" in categories:
        policy_result["status"] = "blocked"
        policy_result["decision"] = "block"
        policy_result["code"] = "POLICY_DENIED"
        policy_result["reason_category"] = "SENSITIVE_PERSONAL_DATA"
        policy_result["user_safe_explanation"] = "This request involves restricted personal data."
        policy_result["suggested_safe_alternative"] = (
            "Request a redacted or aggregated summary if your role allows it."
        )
        policy_result["matched_rules"] = list(
            set(policy_result["matched_rules"] + ["PII_HIGH"])
        )
        policy_result["risk_level"] = "high"
        policy_result["risk_score"] = max(policy_result["risk_score"], 85)

    if "CREDENTIALS" in categories:
        policy_result["status"] = "blocked"
        policy_result["decision"] = "block"
        policy_result["code"] = "POLICY_DENIED"
        policy_result["reason_category"] = "CREDENTIALS"
        policy_result["user_safe_explanation"] = (
            "Credentials, secrets, and private keys cannot be disclosed."
        )
        policy_result["suggested_safe_alternative"] = (
            "Ask for a high-level explanation without sensitive values."
        )
        policy_result["matched_rules"] = list(
            set(policy_result["matched_rules"] + ["CREDENTIALS"])
        )
        policy_result["risk_level"] = "high"
        policy_result["risk_score"] = max(policy_result["risk_score"], 90)

    if (
        "SOURCE_CODE" in categories
        and (
            "EXTERNAL_SHARING" in categories
            or action == "upload_to_external_ai"
            or " into ai" in normalized_text
            or " external_ai" in normalized_text
        )
    ):
        policy_result["status"] = "blocked"
        policy_result["decision"] = "block"
        policy_result["code"] = "POLICY_DENIED"
        policy_result["reason_category"] = "SOURCE_CODE_EXTERNALIZATION"
        policy_result["user_safe_explanation"] = (
            "Uploading or sharing internal source code with external AI tools is restricted."
        )
        policy_result["suggested_safe_alternative"] = (
            "Ask for an internal architecture summary or a scoped explanation using approved internal sources."
        )
        policy_result["matched_rules"] = list(
            set(policy_result["matched_rules"] + ["EXTERNAL_AI_RISK", "SOURCE_CODE_EXTERNALIZATION"])
        )
        policy_result["risk_level"] = "high"
        policy_result["risk_score"] = max(policy_result["risk_score"], 90)

    return policy_result


@router.post("/chat")
def guarded_chat(request: ChatRequest, user_id: str = Depends(get_current_user_id)):
    request_id = str(uuid.uuid4())
    total_start = time.perf_counter()

    try:
        t0 = time.perf_counter()
        user_context = get_user_context(user_id)
        user_context_ms = round((time.perf_counter() - t0) * 1000, 2)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"User context error: {str(e)}")

    t1 = time.perf_counter()
    understanding = understand_request(request.text)
    policy_result = analyze_text(understanding["normalized_text"], user_context)
    policy_result = apply_semantic_policy_overrides(policy_result, understanding)
    policy_ms = round((time.perf_counter() - t1) * 1000, 2)

    blocked_response = {
        "status": "blocked",
        "answer": None,
        "policy": build_policy_response(policy_result, understanding),
        "selected_sources": [],
        "source_references": [],
        "retrieval_count": 0,
        "metadata": {
            "request_id": request_id,
            "normalized_text": understanding["normalized_text"],
            "prompt_injection_hits": understanding["prompt_injection_hits"],
            "timings_ms": {
                "user_context": user_context_ms,
                "policy": policy_ms,
                "total": round((time.perf_counter() - total_start) * 1000, 2),
            },
        },
    }

    if policy_result["status"] == "blocked":
        log_policy_event(
            event_type="CHAT_BLOCKED_BY_POLICY",
            payload={
                "request_id": request_id,
                "user_id": user_context["user_id"],
                "query": request.text,
                "normalized_text": understanding["normalized_text"],
                "categories": understanding["categories"],
                "action": understanding["action"],
                "policy": policy_result,
            },
        )
        return JSONResponse(status_code=403, content=blocked_response)

    normalized = understanding["normalized_text"].strip()
    if normalized in SMALL_TALK_INPUTS:
        response = {
            "status": "allowed",
            "answer": SMALL_TALK_INPUTS[normalized],
            "policy": build_policy_response(policy_result, understanding),
            "selected_sources": [],
            "source_references": [],
            "retrieval_count": 0,
            "metadata": {
                "request_id": request_id,
                "normalized_text": normalized,
                "fast_path": "small_talk",
                "timings_ms": {
                    "user_context": user_context_ms,
                    "policy": policy_ms,
                    "retrieval": 0,
                    "generation": 0,
                    "total": round((time.perf_counter() - total_start) * 1000, 2),
                },
            },
        }
        return response
    
    route_decision = decide_query_route(request.text)
    if route_decision["route"] == "general_concept":
        t_gen = time.perf_counter()
        answer = generate_general_answer(request.text)
        generation_ms = round((time.perf_counter() - t_gen) * 1000, 2)

        output_check = validate_generated_answer(answer)
        final_status = "allowed" if output_check["status"] == "clean" else "allowed_with_redaction"

        response = {
            "status": final_status,
            "answer": output_check["answer"],
            "policy": {
                **build_policy_response(policy_result, understanding),
                "code": None,
                "reason_category": None,
                "user_safe_explanation": None,
                "suggested_safe_alternative": None,
            },
            "selected_sources": [],
            "source_references": [],
            "retrieval_count": 0,
            "metadata": {
                "request_id": request_id,
                "normalized_text": understanding["normalized_text"],
                "query_route": route_decision,
                "output_validation": output_check["status"],
                "output_hits": output_check["hits"],
                "timings_ms": {
                    "user_context": user_context_ms,
                    "policy": policy_ms,
                    "retrieval": 0,
                    "generation": generation_ms,
                    "total": round((time.perf_counter() - total_start) * 1000, 2),
                },
            },
        }

        log_policy_event(
            event_type="CHAT_GENERAL_CONCEPT_RESPONSE",
            payload={
                "request_id": request_id,
                "user_id": user_context["user_id"],
                "query": request.text,
                "response": response,
            },
        )

        return response

    try:
        t2 = time.perf_counter()
        retrieval = retrieve_authorized_chunks(request.text, user_context, top_k=request.top_k)
        chunks = retrieval["chunks"]
        retrieval_ms = round((time.perf_counter() - t2) * 1000, 2)
    except Exception as e:
        log_policy_event(
            event_type="CHAT_RETRIEVAL_ERROR",
            payload={
                "request_id": request_id,
                "user_id": user_context["user_id"],
                "query": request.text,
                "error": str(e),
            },
        )
        raise HTTPException(status_code=500, detail=f"Retrieval error: {str(e)}")

    if not chunks:
        response = {
            "status": "clarify",
            "answer": (
                "I could not find authorized internal content for that request. "
                "Try narrowing the request to a known department-approved resource or document type."
            ),
            "policy": {
                **build_policy_response(policy_result, understanding),
                "code": None,
                "reason_category": None,
                "user_safe_explanation": None,
                "suggested_safe_alternative": (
                    "Ask for a specific repo, page tree, runbook, or internal document within your approved scope."
                ),
            },
            "selected_sources": retrieval["selected_sources"],
            "source_references": [],
            "retrieval_count": 0,
            "metadata": {
                "request_id": request_id,
                "normalized_text": understanding["normalized_text"],
                "selection_reasoning": retrieval["selection_reasoning"],
                "timings_ms": {
                    "user_context": user_context_ms,
                    "policy": policy_ms,
                    "retrieval": retrieval_ms,
                    "generation": 0,
                    "total": round((time.perf_counter() - total_start) * 1000, 2),
                },
            },
        }

        log_policy_event(event_type="CHAT_NO_AUTHORIZED_CONTEXT", payload=response)
        return response

    t3 = time.perf_counter()
    answer = generate_answer(user_context, request.text, chunks)
    generation_ms = round((time.perf_counter() - t3) * 1000, 2)

    output_check = validate_generated_answer(answer)
    final_status = "allowed" if output_check["status"] == "clean" else "allowed_with_redaction"

    response = {
        "status": final_status,
        "answer": output_check["answer"],
        "policy": {
            **build_policy_response(policy_result, understanding),
            "code": None,
            "reason_category": None,
            "user_safe_explanation": None,
            "suggested_safe_alternative": None,
        },
        "selected_sources": retrieval["selected_sources"],
        "source_references": [
            {
                "chunk_id": c["chunk_id"],
                "document_id": c["document_id"],
                "title": c["title"],
                "resource_path": c["resource_path"],
                "source_type": c["source_type"],
                "resource_name": c["resource_name"],
                "score": c["score"],
            }
            for c in chunks
        ],
        "retrieval_count": len(chunks),
        "metadata": {
            "request_id": request_id,
            "normalized_text": understanding["normalized_text"],
            "selection_reasoning": retrieval["selection_reasoning"],
            "output_validation": output_check["status"],
            "output_hits": output_check["hits"],
            "timings_ms": {
                "user_context": user_context_ms,
                "policy": policy_ms,
                "retrieval": retrieval_ms,
                "generation": generation_ms,
                "total": round((time.perf_counter() - total_start) * 1000, 2),
            },
        },
    }

    log_policy_event(
        event_type="CHAT_GENERATED_RESPONSE",
        payload={
            "request_id": request_id,
            "user_id": user_context["user_id"],
            "query": request.text,
            "response": response,
        },
    )

    return response


@router.post("/chat/stream")
def guarded_chat_stream(request: ChatRequest, user_id: str = Depends(get_current_user_id)):
    request_id = str(uuid.uuid4())
    total_start = time.perf_counter()

    try:
        t0 = time.perf_counter()
        user_context = get_user_context(user_id)
        user_context_ms = round((time.perf_counter() - t0) * 1000, 2)
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"User context error: {str(e)}")

    t1 = time.perf_counter()
    understanding = understand_request(request.text)
    policy_result = analyze_text(understanding["normalized_text"], user_context)
    policy_result = apply_semantic_policy_overrides(policy_result, understanding)
    policy_ms = round((time.perf_counter() - t1) * 1000, 2)

    # if policy_result["status"] == "blocked":
    #     raise HTTPException(
    #         status_code=403,
    #         detail={
    #             "status": "blocked",
    #             "answer": None,
    #             "policy": build_policy_response(policy_result, understanding),
    #             "selected_sources": [],
    #             "source_references": [],
    #             "retrieval_count": 0,
    #             "metadata": {
    #                 "request_id": request_id,
    #                 "normalized_text": understanding["normalized_text"],
    #                 "prompt_injection_hits": understanding["prompt_injection_hits"],
    #                 "timings_ms": {
    #                     "user_context": user_context_ms,
    #                     "policy": policy_ms,
    #                     "total": round((time.perf_counter() - total_start) * 1000, 2),
    #                 },
    #             },
    #         },
    #     )
    if policy_result["status"] == "blocked":
        blocked_payload = {
            "request_id": request_id,
            "user_id": user_context["user_id"],
            "query": request.text,
            "normalized_text": understanding["normalized_text"],
            "categories": understanding["categories"],
            "action": understanding["action"],
            "policy": policy_result,
        }

        log_policy_event(
            event_type="CHAT_BLOCKED_BY_POLICY",
            payload=blocked_payload,
        )

        raise HTTPException(
            status_code=403,
            detail={
                "status": "blocked",
                "answer": None,
                "policy": {
                    "status": policy_result["status"],
                    "decision": policy_result["decision"],
                    "code": policy_result.get("code"),
                    "reason_category": policy_result.get("reason_category"),
                    "user_safe_explanation": policy_result.get("user_safe_explanation"),
                    "suggested_safe_alternative": policy_result.get("suggested_safe_alternative"),
                    "matched_rules": policy_result["matched_rules"],
                    "categories": understanding["categories"],
                    "action": understanding["action"],
                    "risk_level": policy_result["risk_level"],
                    "risk_score": policy_result["risk_score"],
                },
                "selected_sources": [],
                "source_references": [],
                "retrieval_count": 0,
                "metadata": {
                    "request_id": request_id,
                    "normalized_text": understanding["normalized_text"],
                    "prompt_injection_hits": understanding["prompt_injection_hits"],
                },
            },
        )
        
    normalized = understanding["normalized_text"].strip()
    if normalized in SMALL_TALK_INPUTS:
        def small_talk_stream():
            yield json.dumps({"type": "start", "request_id": request_id}) + "\n"
            yield json.dumps({
                "type": "final",
                "data": {
                    "status": "allowed",
                    "answer": SMALL_TALK_INPUTS[normalized],
                    "policy": build_policy_response(policy_result, understanding),
                    "selected_sources": [],
                    "source_references": [],
                    "retrieval_count": 0,
                    "metadata": {
                        "request_id": request_id,
                        "normalized_text": normalized,
                        "fast_path": "small_talk",
                        "timings_ms": {
                            "user_context": user_context_ms,
                            "policy": policy_ms,
                            "retrieval": 0,
                            "generation": 0,
                            "total": round((time.perf_counter() - total_start) * 1000, 2),
                        },
                    },
                }
            }) + "\n"

        return StreamingResponse(small_talk_stream(), media_type="application/x-ndjson")

    route_decision = decide_query_route(request.text)
    if route_decision["route"] == "general_concept":
        def general_concept_stream():
            full_answer = ""
            generation_start = time.perf_counter()

            yield json.dumps({"type": "token", "token": " "}) + "\n"

            for token in stream_general_answer(request.text):
                full_answer += token
                yield json.dumps({"type": "token", "token": token}) + "\n"

            generation_ms = round((time.perf_counter() - generation_start) * 1000, 2)
            output_check = validate_generated_answer(full_answer)
            final_status = "allowed" if output_check["status"] == "clean" else "allowed_with_redaction"

            final_payload = {
                "status": final_status,
                "answer": output_check["answer"],
                "policy": {
                    **build_policy_response(policy_result, understanding),
                    "code": None,
                    "reason_category": None,
                    "user_safe_explanation": None,
                    "suggested_safe_alternative": None,
                },
                "selected_sources": [],
                "source_references": [],
                "retrieval_count": 0,
                "metadata": {
                    "request_id": request_id,
                    "normalized_text": understanding["normalized_text"],
                    "query_route": route_decision,
                    "output_validation": output_check["status"],
                    "output_hits": output_check["hits"],
                    "timings_ms": {
                        "user_context": user_context_ms,
                        "policy": policy_ms,
                        "retrieval": 0,
                        "generation": generation_ms,
                        "total": round((time.perf_counter() - total_start) * 1000, 2),
                    },
                },
            }

            yield json.dumps({"type": "final", "data": final_payload}) + "\n"

        return StreamingResponse(
            general_concept_stream(),
            media_type="application/x-ndjson",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )
    
    t2 = time.perf_counter()
    retrieval = retrieve_authorized_chunks(request.text, user_context, top_k=request.top_k)
    chunks = retrieval["chunks"]
    retrieval_ms = round((time.perf_counter() - t2) * 1000, 2)

    if not chunks:
        def no_context_stream():
            yield json.dumps({"type": "start", "request_id": request_id}) + "\n"
            yield json.dumps({
                "type": "final",
                "data": {
                    "status": "clarify",
                    "answer": (
                        "I could not find authorized internal content for that request. "
                        "Try narrowing the request to a known department-approved resource or document type."
                    ),
                    "policy": {
                        **build_policy_response(policy_result, understanding),
                        "code": None,
                        "reason_category": None,
                        "user_safe_explanation": None,
                        "suggested_safe_alternative": (
                            "Ask for a specific repo, page tree, runbook, or internal document within your approved scope."
                        ),
                    },
                    "selected_sources": retrieval["selected_sources"],
                    "source_references": [],
                    "retrieval_count": 0,
                    "metadata": {
                        "request_id": request_id,
                        "normalized_text": understanding["normalized_text"],
                        "selection_reasoning": retrieval["selection_reasoning"],
                        "timings_ms": {
                            "user_context": user_context_ms,
                            "policy": policy_ms,
                            "retrieval": retrieval_ms,
                            "generation": 0,
                            "total": round((time.perf_counter() - total_start) * 1000, 2),
                        },
                    },
                }
            }) + "\n"

        return StreamingResponse(no_context_stream(), media_type="application/x-ndjson")

    def event_stream():
        full_answer = ""
        generation_start = time.perf_counter()

        # yield json.dumps({
        #     "type": "start",
        #     "request_id": request_id,
        # }) + "\n"
        yield json.dumps({
        "type": "token",
        "token": " ",
        }) + "\n"

        for token in stream_answer(user_context, request.text, chunks):
            full_answer += token
            yield json.dumps({"type": "token", "token": token}) + "\n"

        generation_ms = round((time.perf_counter() - generation_start) * 1000, 2)

        output_check = validate_generated_answer(full_answer)
        final_status = "allowed" if output_check["status"] == "clean" else "allowed_with_redaction"

        final_payload = {
            "status": final_status,
            "answer": output_check["answer"],
            "policy": {
                **build_policy_response(policy_result, understanding),
                "code": None,
                "reason_category": None,
                "user_safe_explanation": None,
                "suggested_safe_alternative": None,
            },
            "selected_sources": retrieval["selected_sources"],
            "source_references": [
                {
                    "chunk_id": c["chunk_id"],
                    "document_id": c["document_id"],
                    "title": c["title"],
                    "resource_path": c["resource_path"],
                    "source_type": c["source_type"],
                    "resource_name": c["resource_name"],
                    "score": c["score"],
                }
                for c in chunks
            ],
            "retrieval_count": len(chunks),
            "metadata": {
                "request_id": request_id,
                "normalized_text": understanding["normalized_text"],
                "selection_reasoning": retrieval["selection_reasoning"],
                "output_validation": output_check["status"],
                "output_hits": output_check["hits"],
                "timings_ms": {
                    "user_context": user_context_ms,
                    "policy": policy_ms,
                    "retrieval": retrieval_ms,
                    "generation": generation_ms,
                    "total": round((time.perf_counter() - total_start) * 1000, 2),
                },
            },
        }

        yield json.dumps({"type": "final", "data": final_payload}) + "\n"

    # return StreamingResponse(event_stream(), media_type="application/x-ndjson")
    return StreamingResponse(
        event_stream(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
        )
