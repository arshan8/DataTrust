def _build_scope_preview(scopes: list[dict]) -> list[dict]:
    return [
        {
            "scope_id": s["scope_id"],
            "resource_name": s["resource_name"],
            "resource_type": s["resource_type"],
            "resource_path": s["resource_path"],
            "min_auth_level": s["min_auth_level"],
        }
        for s in scopes
    ]


def search_confluence(query: str, allowed_scopes: list[dict]) -> dict:
    matched = [s for s in allowed_scopes if s["source_type"] == "CONFLUENCE"]
    return {
        "source": "CONFLUENCE",
        "reasoning": "Selected because the query appears documentation or page-oriented.",
        "action": "plan_search",
        "status": "planned",
        "allowed_scope_count": len(matched),
        "matched_scopes": _build_scope_preview(matched),
    }


def search_github(query: str, allowed_scopes: list[dict]) -> dict:
    matched = [s for s in allowed_scopes if s["source_type"] == "GITHUB"]
    return {
        "source": "GITHUB",
        "reasoning": "Selected because the query appears repo/code/architecture-related.",
        "action": "plan_search",
        "status": "planned",
        "allowed_scope_count": len(matched),
        "matched_scopes": _build_scope_preview(matched),
    }


def search_gdrive(query: str, allowed_scopes: list[dict]) -> dict:
    matched = [s for s in allowed_scopes if s["source_type"] == "GDRIVE"]
    return {
        "source": "GDRIVE",
        "reasoning": "Selected because the query appears document/folder/file-related.",
        "action": "plan_search",
        "status": "planned",
        "allowed_scope_count": len(matched),
        "matched_scopes": _build_scope_preview(matched),
    }