from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from .clause import Clause

class TimelinePosition(BaseModel):
    percentage: float = Field(..., ge=0.0, le=100.0, description="Position percentage in document")
    visual_indicator: str = Field(..., description="Visual indicator type")

class ClauseTimelineItem(BaseModel):
    clause_id: str
    sequence_number: int
    clause_title: str
    clause_text: str
    clause_type: str
    severity_level: int
    severity_color: str
    plain_language_explanation: str
    risk_factors: List[str]
    legal_implications: str
    compliance_flags: List[str]
    related_clauses: List[str]
    timeline_position: TimelinePosition

class DocumentMetadata(BaseModel):
    title: str
    document_type: str
    total_clauses: int
    overall_risk_score: float = Field(..., ge=0.0, le=5.0)
    processing_time: str
    compliance_status: str = Field(..., description="compliant, partially_compliant, non_compliant")

class DocumentSummary(BaseModel):
    high_risk_clauses: int
    medium_risk_clauses: int
    low_risk_clauses: int
    critical_issues: List[str]
    recommendations: List[str]
    compliance_score: float = Field(..., ge=0.0, le=100.0)
    overall_sentiment: str = Field(..., description="low_risk, moderate_risk, high_risk, critical_risk")

class TimelineNavigation(BaseModel):
    total_steps: int
    critical_checkpoints: List[int]  # Clause sequence numbers
    recommended_flow: List[int]     # Suggested reading order

class DocumentAnalysisResponse(BaseModel):
    document_id: str
    document_metadata: DocumentMetadata
    clause_timeline: List[ClauseTimelineItem]
    document_summary: DocumentSummary
    timeline_navigation: TimelineNavigation

class ClauseDetailsResponse(BaseModel):
    clause: Clause
    related_clauses: List[Clause] = Field(default_factory=list)
    contextual_explanation: Optional[str] = None

class RAGQueryRequest(BaseModel):
    query: str = Field(..., description="User question about clauses")
    document_id: Optional[str] = None
    clause_ids: Optional[List[str]] = None
    context_limit: int = Field(default=5, ge=1, le=20)

class RAGQueryResponse(BaseModel):
    query: str
    answer: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    related_clauses: List[str] = Field(default_factory=list)

class ErrorResponse(BaseModel):
    error: str
    error_code: str
    details: Optional[Dict[str, Any]] = None

class ProcessingStatusResponse(BaseModel):
    document_id: str
    status: str
    progress_percentage: Optional[float] = None
    estimated_time_remaining: Optional[str] = None
    message: Optional[str] = None
