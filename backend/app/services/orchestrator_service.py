import logging
from typing import List, Dict

from app.services.resource_scope_service import get_allowed_resource_scopes
from app.services.connectors import search_confluence, search_github, search_gdrive

logger = logging.getLogger(__name__)

def choose_sources(query: str, allowed_scopes: List[Dict], user_context: dict | None = None) -> tuple[List[str], List[str]]:
    lowered = query.lower()
    selected = set()
    reasoning = []

    allowed_source_types = {s["source_type"] for s in allowed_scopes}
    # HARD GUARD (prevents DB mistakes from leaking access)
    department = user_context.get("department") if user_context else None

    print("DEBUG choose_sources department:", department)
    print("DEBUG choose_sources allowed_source_types BEFORE:", allowed_source_types)

    if department and department != "TECH":
        allowed_source_types.discard("GITHUB")

    print("DEBUG choose_sources allowed_source_types AFTER:", allowed_source_types)
    
    github_terms = [
        "repo", "repository", "code", "commit", "pull request", "pr",
        "architecture", "deployment", "backend", "frontend", "service",
        "api", "implementation", "source code"
    ]

    confluence_terms = [
        "policy", "page", "confluence", "documentation", "docs", "runbook",
        "runbooks", "guide", "playbook", "procedure", "design doc", "architecture", "overview", "backend", "admin",
        "architecture doc", "incident", "postmortem", "rca"
    ]

    gdrive_terms = [
        "drive", "folder", "document", "slides", "file", "campaign",
        "spreadsheet", "sheet", "presentation"
    ]

    github_match = any(term in lowered for term in github_terms)
    confluence_match = any(term in lowered for term in confluence_terms)
    gdrive_match = any(term in lowered for term in gdrive_terms)

    if github_match and "GITHUB" in allowed_source_types:
        selected.add("GITHUB")
        reasoning.append("Selected GITHUB because the query appears repo/code/architecture-related.")

    if confluence_match and "CONFLUENCE" in allowed_source_types:
        selected.add("CONFLUENCE")
        reasoning.append("Selected CONFLUENCE because the query appears documentation or page-oriented.")

    if gdrive_match and "GDRIVE" in allowed_source_types:
        selected.add("GDRIVE")
        reasoning.append("Selected GDRIVE because the query appears document/file/folder-oriented.")

    # Important: technical documentation often lives in both GitHub and Confluence
    technical_doc_terms = [
        "architecture", "deployment", "design", "runbook", "docs", "documentation",
        "backend", "frontend", "service", "api", "incident", "rca"
    ]

    if any(term in lowered for term in technical_doc_terms):
        if "GITHUB" in allowed_source_types:
            selected.add("GITHUB")
        if "CONFLUENCE" in allowed_source_types:
            selected.add("CONFLUENCE")

        if "GITHUB" in allowed_source_types and "CONFLUENCE" in allowed_source_types:
            reasoning.append(
                "Selected both GITHUB and CONFLUENCE because technical docs may exist in repos and wiki/runbook pages."
            )

    if not selected:
        selected = allowed_source_types
        reasoning.append("No strong source hint found, so all allowed source types were selected.")

    logger.info("SOURCE_SELECTION_DONE query=%r selected=%s reasoning=%s", query, list(selected), reasoning)
    return list(selected), reasoning


def build_retrieval_plan(query: str, user_context: dict) -> dict:
    allowed_scopes = get_allowed_resource_scopes(user_context)
    selected_sources, reasoning = choose_sources(query, allowed_scopes, user_context)

    # Filter scopes by selected sources only
    selected_scopes = [
        scope for scope in allowed_scopes
        if scope["source_type"] in selected_sources
    ]

    confluence_scopes = [
        scope for scope in selected_scopes
        if scope["source_type"] == "CONFLUENCE"
    ]
    github_scopes = [
        scope for scope in selected_scopes
        if scope["source_type"] == "GITHUB"
    ]
    gdrive_scopes = [
        scope for scope in selected_scopes
        if scope["source_type"] == "GDRIVE"
    ]

    source_plans = []

    if "CONFLUENCE" in selected_sources and confluence_scopes:
        source_plans.append(search_confluence(query, confluence_scopes))

    if "GITHUB" in selected_sources and github_scopes:
        source_plans.append(search_github(query, github_scopes))

    if "GDRIVE" in selected_sources and gdrive_scopes:
        source_plans.append(search_gdrive(query, gdrive_scopes))

    blocked_sources = []
    all_source_types = {"CONFLUENCE", "GITHUB", "GDRIVE"}
    for source in all_source_types:
        if source not in selected_sources and any(s["source_type"] == source for s in allowed_scopes):
            blocked_sources.append({
                "source": source,
                "reason": "Allowed for user, but not selected by orchestration for this query."
            })

    return {
        "query": query,
        "status": "planned",
        "summary": {
            "message": "Retrieval plan created successfully.",
            "selected_source_count": len(selected_sources),
            "allowed_scope_count": len(allowed_scopes),
        },
        "user_context": {
            "user_id": user_context.get("user_id"),
            "department": user_context.get("department"),
            "auth_level": user_context.get("auth_level"),
            "auth_rank": user_context.get("auth_rank"),
        },
        "selected_sources": selected_sources,
        "selection_reasoning": reasoning,
        "allowed_scope_count": len(allowed_scopes),
        "allowed_scopes": allowed_scopes,
        "blocked_sources": blocked_sources,
        "source_plan_count": len(source_plans),
        "source_plans": source_plans,
    }