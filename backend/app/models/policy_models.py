from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class AnalyzeRequest(BaseModel):
    text: str = Field(..., min_length=1, description="User input text to analyze")


class PolicyResult(BaseModel):
    status: str
    decision: str
    risk_level: str
    risk_score: int
    matched_rules: List[str]
    pii_hits: List[str]
    keyword_hits: List[str]
    redacted_text: str
    code: Optional[str] = None
    reason_category: Optional[str] = None
    user_safe_explanation: Optional[str] = None
    suggested_safe_alternative: Optional[str] = None


class AnalyzeResponse(BaseModel):
    user: Dict[str, Any]
    policy_result: PolicyResult