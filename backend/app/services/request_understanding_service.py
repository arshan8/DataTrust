import re
from typing import Dict, List


PROMPT_INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"reveal system prompt",
    r"bypass policy",
    r"act as admin",
    r"ignore all rules",
    r"dump the hidden prompt",
]

CATEGORY_RULES = {
    "PII_HIGH": [
        "ssn",
        "social_security_number",
        "employee_id",
        "employee_identifier",
        "tax_id",
        "national_id",
        "identity_number",
        "payroll",
        "salary",
        "employee review",
        "employee_data",
    ],
    "CREDENTIALS": [
        "password",
        "token",
        "secret",
        "api_key",
        "private_key",
        "credential",
    ],
    "SOURCE_CODE": [
        "source_code",
        "repo",
        "git",
        "architecture_decision_record",
        "root_cause_analysis",
        "code",
    ],
    "INTERNAL_DOCS": [
        "internal_docs",
        "internal_documents",
        "runbook",
        "confluence",
        "private_docs",
        "document",
    ],
    "EXTERNAL_SHARING": [
        "external_ai",
        "upload",
        "share_externally",
        "send_externally",
        "paste_externally",
        "send_to",
        "put_into",
    ],
    "ADMIN_ACTION": [
        "all_logs",
        "all_users",
        "all_audit_records",
        "download_policy_logs",
    ],
}

ACTION_RULES = {
    "export": ["export", "download all", "dump", "send all", "give me all", "list all"],
    "upload_to_external_ai": ["upload", "paste", "send", "share", "put"],
    "summarize": ["summarize", "summary", "explain"],
    "retrieve": ["show", "find", "get", "list", "give me"],
    "admin_action": ["delete", "disable", "override", "grant access"],
}


def normalize_prompt(text: str) -> str:
    value = text.lower()

    # normalize common punctuated SSN variants before stripping punctuation
    value = re.sub(r"\bs[\W_]*s[\W_]*n\b", " ssn ", value)

    # normalize common phrases
    value = re.sub(r"\bsocial security number(s)?\b", " social_security_number ", value)
    value = re.sub(r"\bemployee id(s)?\b", " employee_id ", value)
    value = re.sub(r"\bemployee identifier(s)?\b", " employee_identifier ", value)
    value = re.sub(r"\btax id(s)?\b", " tax_id ", value)
    value = re.sub(r"\bnational id(s)?\b", " national_id ", value)
    value = re.sub(r"\bidentity number(s)?\b", " identity_number ", value)

    value = re.sub(r"\bsource code\b", " source_code ", value)
    value = re.sub(r"\binternal docs\b", " internal_docs ", value)
    value = re.sub(r"\binternal documents\b", " internal_documents ", value)
    value = re.sub(r"\bemployee data\b", " employee_data ", value)
    value = re.sub(r"\bapi key\b", " api_key ", value)
    value = re.sub(r"\bprivate key\b", " private_key ", value)

    # external AI tools
    value = re.sub(r"\bchatgpt\b", " external_ai ", value)
    value = re.sub(r"\bclaude\b", " external_ai ", value)
    value = re.sub(r"\bgemini\b", " external_ai ", value)
    value = re.sub(r"\bcopilot\b", " external_ai ", value)
    value = re.sub(r"\bopenai\b", " external_ai ", value)

    # action phrases
    value = re.sub(r"\bshare externally\b", " share_externally ", value)
    value = re.sub(r"\bsend externally\b", " send_externally ", value)
    value = re.sub(r"\bpaste externally\b", " paste_externally ", value)
    value = re.sub(r"\bsend to\b", " send_to ", value)
    value = re.sub(r"\bput into\b", " put_into ", value)

    # remove remaining punctuation
    value = re.sub(r"[\r\n\t]+", " ", value)
    value = re.sub(r"[^a-z0-9_ ]+", " ", value)
    value = re.sub(r"\s+", " ", value).strip()

    return value


def detect_prompt_injection(normalized: str) -> List[str]:
    hits = []
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, normalized):
            hits.append("PROMPT_INJECTION")
            break
    return hits


def classify_categories(normalized: str) -> List[str]:
    categories = []

    for category, phrases in CATEGORY_RULES.items():
        if any(phrase in normalized for phrase in phrases):
            categories.append(category)

    # compound rule: source code + external AI
    if ("source_code" in normalized or "repo" in normalized or "code" in normalized) and (
        "external_ai" in normalized or " ai " in f" {normalized} "
    ):
        if "SOURCE_CODE" not in categories:
            categories.append("SOURCE_CODE")
        if "EXTERNAL_SHARING" not in categories:
            categories.append("EXTERNAL_SHARING")

    # compound rule: employee id requests are also high-risk PII
    if "employee_id" in normalized or "employee_identifier" in normalized:
        if "PII_HIGH" not in categories:
            categories.append("PII_HIGH")

    # compound rule: plain ssn
    if "ssn" in normalized or "social_security_number" in normalized:
        if "PII_HIGH" not in categories:
            categories.append("PII_HIGH")

    return categories or ["BENIGN_INFORMATIONAL"]


def detect_action(normalized: str) -> str:
    if (
        any(v in normalized for v in ["upload", "paste", "send", "share", "put"])
        and ("external_ai" in normalized or " ai " in f" {normalized} ")
    ):
        return "upload_to_external_ai"

    for action, phrases in ACTION_RULES.items():
        if any(phrase in normalized for phrase in phrases):
            return action

    return "answer"


def understand_request(text: str) -> Dict:
    normalized = normalize_prompt(text)
    categories = classify_categories(normalized)
    injection_hits = detect_prompt_injection(normalized)
    action = detect_action(normalized)

    if injection_hits and "PROMPT_INJECTION" not in categories:
        categories.append("PROMPT_INJECTION")

    return {
        "original_text": text,
        "normalized_text": normalized,
        "categories": categories,
        "action": action,
        "prompt_injection_hits": injection_hits,
    }