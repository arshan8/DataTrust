from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any


class ChatRequest(BaseModel):
    text: str = Field(..., min_length=1, description="User prompt")
    top_k: int = Field(default=5, ge=1, le=10)


class SourceReference(BaseModel):
    chunk_id: int
    document_id: int
    title: Optional[str] = None
    resource_path: Optional[str] = None
    source_type: Optional[str] = None
    resource_name: Optional[str] = None
    score: float


class ChatPolicy(BaseModel):
    status: str
    decision: str
    code: Optional[str] = None
    reason_category: Optional[str] = None
    user_safe_explanation: Optional[str] = None
    suggested_safe_alternative: Optional[str] = None
    matched_rules: List[str]
    categories: List[str]
    action: str
    risk_level: str
    risk_score: int


class ChatResponse(BaseModel):
    status: str
    answer: Optional[str] = None
    policy: ChatPolicy
    selected_sources: List[str]
    source_references: List[SourceReference]
    retrieval_count: int
    metadata: Dict[str, Any]