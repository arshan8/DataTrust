import re


OUTPUT_PII_PATTERNS = {
    "PII_EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
    "PII_PHONE": r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
    "PII_SSN": r"\b\d{3}-\d{2}-\d{4}\b",
    "SECRET_AWS_KEY": r"\bAKIA[0-9A-Z]{16}\b",
    "SECRET_PRIVATE_KEY_BLOCK": r"-----BEGIN (?:RSA|EC|OPENSSH|DSA|PRIVATE KEY)-----",
}


def scan_output(answer: str) -> list[str]:
    hits = []
    for code, pattern in OUTPUT_PII_PATTERNS.items():
        if re.search(pattern, answer, flags=re.IGNORECASE):
            hits.append(code)
    return hits


def redact_output(answer: str) -> str:
    redacted = answer
    redacted = re.sub(OUTPUT_PII_PATTERNS["PII_EMAIL"], "[REDACTED_EMAIL]", redacted, flags=re.IGNORECASE)
    redacted = re.sub(OUTPUT_PII_PATTERNS["PII_PHONE"], "[REDACTED_PHONE]", redacted, flags=re.IGNORECASE)
    redacted = re.sub(OUTPUT_PII_PATTERNS["PII_SSN"], "[REDACTED_SSN]", redacted, flags=re.IGNORECASE)
    redacted = re.sub(OUTPUT_PII_PATTERNS["SECRET_AWS_KEY"], "[REDACTED_AWS_KEY]", redacted, flags=re.IGNORECASE)
    redacted = re.sub(OUTPUT_PII_PATTERNS["SECRET_PRIVATE_KEY_BLOCK"], "[REDACTED_PRIVATE_KEY]", redacted, flags=re.IGNORECASE)
    return redacted


def validate_generated_answer(answer: str) -> dict:
    hits = scan_output(answer)
    if not hits:
        return {
            "status": "clean",
            "answer": answer,
            "hits": [],
        }

    return {
        "status": "redacted",
        "answer": redact_output(answer),
        "hits": hits,
    }