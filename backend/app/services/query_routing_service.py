import re


GENERAL_CONCEPT_STARTERS = [
    "what is",
    "what are",
    "explain",
    "define",
    "how does",
    "how do",
    "why does",
    "why do",
    "difference between",
    "compare",
]


INTERNAL_HINTS = [
    "datatrust",
    "our",
    "internal",
    "company",
    "backend architecture",
    "frontend architecture",
    "runbook",
    "architecture docs",
    "deployment docs",
    "system overview",
    "source reference",
    "github",
    "confluence",
    "google drive",
    "drive",
    "repo",
    "repository",
    "document",
    "docs",
    "page",
    "folder",
    "tech",
    "hr",
    "finance",
    "operations",
    "l1",
    "l2",
    "l3",
]


SENSITIVE_OR_POLICY_HINTS = [
    "ssn",
    "s.s.n",
    "social security",
    "employee id",
    "payroll",
    "salary",
    "password",
    "secret",
    "token",
    "api key",
    "private key",
    "dump",
    "bypass",
    "ignore instructions",
]


def normalize_for_routing(text: str) -> str:
    value = (text or "").lower().strip()
    value = re.sub(r"\s+", " ", value)
    return value


def is_small_talk(text: str) -> bool:
    q = normalize_for_routing(text)
    return q in {
        "hi",
        "hello",
        "hey",
        "thanks",
        "thank you",
        "good morning",
        "good afternoon",
        "good evening",
    }


def is_policy_sensitive_hint(text: str) -> bool:
    q = normalize_for_routing(text)
    return any(term in q for term in SENSITIVE_OR_POLICY_HINTS)


def is_internal_knowledge_query(text: str) -> bool:
    q = normalize_for_routing(text)

    if any(term in q for term in INTERNAL_HINTS):
        return True

    # Direct source targeting examples:
    # /github:"src/api/chat.ts"
    # /confluence:"TECH/Page"
    # /drive:"folder/file"
    if q.startswith("/github:") or q.startswith("/confluence:") or q.startswith("/drive:"):
        return True

    return False


def is_general_conceptual_query(text: str) -> bool:
    q = normalize_for_routing(text)

    if is_policy_sensitive_hint(q):
        return False

    if is_internal_knowledge_query(q):
        return False

    return any(q.startswith(starter) for starter in GENERAL_CONCEPT_STARTERS)


def decide_query_route(text: str) -> dict:
    q = normalize_for_routing(text)

    if is_small_talk(q):
        return {
            "route": "small_talk",
            "reason": "Small conversational prompt does not require retrieval or generation.",
        }

    if is_general_conceptual_query(q):
        return {
            "route": "general_concept",
            "reason": "General conceptual question can be answered without internal retrieval.",
        }

    return {
        "route": "internal_rag",
        "reason": "Query appears to need authorized internal retrieval or normal guarded processing.",
    }