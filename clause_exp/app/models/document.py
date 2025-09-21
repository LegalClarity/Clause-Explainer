from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime
from bson import ObjectId

class DocumentMetadata(BaseModel):
    file_size: int
    file_type: str
    language: str = "en"

class DocumentBase(BaseModel):
    document_id: str = Field(..., description="Unique document identifier")
    title: str
    document_type: str = Field(..., description="Document type: rental_agreement, loan_contract, terms_of_service")
    file_path: str
    extracted_text: str
    total_clauses: int = 0
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    processing_status: str = Field(default="pending", description="Status: pending, processing, completed, failed")
    metadata: DocumentMetadata
    user_id: Optional[str] = Field(default=None, description="User ID for data isolation")

class DocumentCreate(DocumentBase):
    """Schema for creating new documents"""
    pass

class DocumentUpdate(BaseModel):
    """Schema for updating documents"""
    title: Optional[str] = None
    processing_status: Optional[str] = None
    total_clauses: Optional[int] = None
    extracted_text: Optional[str] = None

class Document(DocumentBase):
    """Full document schema with database ID"""
    id: Optional[str] = Field(default=None, alias="_id")

    class Config:
        allow_population_by_field_name = True
        json_encoders = {
            ObjectId: str
        }

class DocumentInDB(Document):
    """Document as stored in database"""
    id: Optional[str] = Field(default=None, alias="_id")

    class Config:
        allow_population_by_field_name = True
