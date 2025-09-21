"""
Request and Response models for API endpoints
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator
from fastapi import UploadFile

from .schemas import DocumentSummary, AudioSummary, Transcription


class DocumentSummarizeRequest(BaseModel):
    """Request model for document summarization"""
    include_financial_analysis: bool = True
    include_risk_assessment: bool = True
    summary_length: str = Field(default="comprehensive", pattern="^(brief|standard|comprehensive)$")
    language_preference: str = Field(default="en", pattern="^[a-z]{2}$")
    
    @validator('summary_length')
    def validate_summary_length(cls, v):
        if v not in ['brief', 'standard', 'comprehensive']:
            raise ValueError('summary_length must be brief, standard, or comprehensive')
        return v


class AudioSummarizeRequest(BaseModel):
    """Request model for audio summarization"""
    session_type: str = Field(default="general", pattern="^(hearing|deposition|consultation|meeting|interview|general)$")
    expected_language: str = Field(default="en-US")
    include_speaker_analysis: bool = True
    include_action_items: bool = True
    summary_length: str = Field(default="comprehensive", pattern="^(brief|standard|comprehensive)$")
    enable_speaker_diarization: bool = True
    
    @validator('session_type')
    def validate_session_type(cls, v):
        valid_types = ['hearing', 'deposition', 'consultation', 'meeting', 'interview', 'general']
        if v not in valid_types:
            raise ValueError(f'session_type must be one of: {", ".join(valid_types)}')
        return v
    
    @validator('summary_length')
    def validate_summary_length(cls, v):
        if v not in ['brief', 'standard', 'comprehensive']:
            raise ValueError('summary_length must be brief, standard, or comprehensive')
        return v


class DocumentSummaryResponse(BaseModel):
    """Response model for document summarization"""
    filename: str
    file_type: str
    file_size_bytes: int
    summary: DocumentSummary
    confidence_score: float
    processing_time_seconds: float
    processed_at: datetime
    cached_result: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AudioSummaryResponse(BaseModel):
    """Response model for audio summarization"""
    filename: str
    file_type: str
    file_size_bytes: int
    duration_seconds: float
    session_type: str
    transcription: Transcription
    summary: AudioSummary
    confidence_score: float
    processing_time_seconds: float
    processed_at: datetime
    cached_result: bool = False
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AudioGenerationResponse(BaseModel):
    """Response model for audio generation from document"""
    document_title: str
    session_type: str
    summary: AudioSummary
    audio_file_path: str
    audio_duration_seconds: float
    processing_time_seconds: float
    processed_at: datetime
    confidence_score: float
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class HealthResponse(BaseModel):
    """Response model for health check"""
    status: str
    timestamp: datetime
    version: str
    services: Dict[str, str]
    uptime_seconds: float
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ErrorResponse(BaseModel):
    """Response model for errors"""
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime
    request_id: Optional[str] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class ProcessingStatus(BaseModel):
    """Model for processing status updates"""
    status: str  # "pending", "processing", "completed", "failed"
    progress_percentage: float
    current_step: str
    estimated_time_remaining: Optional[float] = None
    message: Optional[str] = None


class BatchProcessingRequest(BaseModel):
    """Request model for batch processing (future enhancement)"""
    files: List[str]  # File paths or URLs
    processing_options: Dict[str, Any]
    callback_url: Optional[str] = None
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")


class FileValidationResponse(BaseModel):
    """Response model for file validation"""
    valid: bool
    file_type: str
    file_size_bytes: int
    estimated_processing_time: Optional[float] = None
    warnings: List[str] = []
    errors: List[str] = []
