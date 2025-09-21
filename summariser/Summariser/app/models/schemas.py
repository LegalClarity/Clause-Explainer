"""
MongoDB schema models for the Legal Summarizer application
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from bson import ObjectId


class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic models"""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError("Invalid ObjectId")
        return ObjectId(v)

    @classmethod
    def __get_pydantic_json_schema__(cls, field_schema):
        field_schema.update(type="string")
        return field_schema


class LegalRisk(BaseModel):
    """Model for legal risk assessment"""
    risk_type: str
    severity: str  # "low", "medium", "high", "critical"
    description: str
    affected_clauses: List[str] = []
    mitigation_suggestions: List[str] = []


class LegalFramework(BaseModel):
    """Model for legal framework references"""
    framework_type: str  # "statute", "regulation", "case_law", etc.
    name: str
    relevance: str
    citations: List[str] = []
    jurisdiction: Optional[str] = None


class FinancialImplications(BaseModel):
    """Model for financial analysis"""
    potential_costs: str
    liability_assessment: str
    recommendations: List[str] = []
    estimated_range: Optional[str] = None


class DocumentSummary(BaseModel):
    """Model for document summary data"""
    key_takeaways: List[str]
    legal_risks: List[LegalRisk]
    legal_frameworks: List[LegalFramework]
    financial_implications: FinancialImplications
    executive_summary: str
    confidence_score: float
    document_type: Optional[str] = None
    complexity_score: Optional[float] = None


class SpeakerSegment(BaseModel):
    """Model for individual speaker segments in transcription"""
    speaker_id: str
    text: str
    start_time: float
    end_time: float
    confidence: float
    emotions: Optional[List[str]] = []


class Transcription(BaseModel):
    """Model for audio transcription data"""
    full_text: str
    speaker_segments: List[SpeakerSegment]
    language_code: str
    overall_confidence: float
    word_count: int


class KeyParticipant(BaseModel):
    """Model for key participants in audio sessions"""
    speaker_id: str
    role: str  # "judge", "attorney", "witness", etc.
    estimated_speaking_time: float
    key_statements: List[str] = []


class ActionItem(BaseModel):
    """Model for action items from audio sessions"""
    description: str
    assigned_to: str
    deadline: Optional[str] = None
    priority: str  # "low", "medium", "high", "urgent"
    status: str = "pending"


class ObjectionRuling(BaseModel):
    """Model for objections and rulings in legal proceedings"""
    timestamp: float
    objection: str
    ruling: str
    context: str
    attorney_making_objection: Optional[str] = None


class AudioSummary(BaseModel):
    """Model for audio summary data"""
    session_overview: str
    key_participants: List[KeyParticipant]
    major_topics: List[str]
    decisions_made: List[str]
    action_items: List[ActionItem]
    legal_citations: List[str]
    objections_rulings: List[ObjectionRuling]
    next_steps: List[str]
    executive_summary: str
    confidence_score: float
    session_type: str
    key_moments: List[Dict[str, Any]] = []


class DocumentSummaryDocument(BaseModel):
    """MongoDB document model for document summaries"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    document_hash: str
    filename: str
    file_type: str
    file_size_bytes: int
    processed_timestamp: datetime
    processing_time_seconds: float
    summary: DocumentSummary
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}


class AudioSummaryDocument(BaseModel):
    """MongoDB document model for audio summaries"""
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    audio_hash: str
    filename: str
    file_type: str
    file_size_bytes: int
    duration_seconds: float
    processed_timestamp: datetime
    processing_time_seconds: float
    session_type: str
    transcription: Transcription
    summary: AudioSummary
    
    class Config:
        populate_by_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
