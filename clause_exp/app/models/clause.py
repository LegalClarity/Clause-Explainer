from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from bson import ObjectId

class PositionInDocument(BaseModel):
    start_char: int
    end_char: int
    page_number: Optional[int] = None

class AnalysisMetadata(BaseModel):
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    ai_model_used: str

class ClauseBase(BaseModel):
    clause_id: str = Field(..., description="Unique clause identifier")
    document_id: str = Field(..., description="Reference to parent document")
    sequence_number: int = Field(..., ge=1, description="Order in document (1, 2, 3...)")
    clause_text: str
    clause_title: str
    clause_type: str = Field(..., description="Type: payment, termination, liability, confidentiality, etc.")
    severity_level: int = Field(..., ge=1, le=5, description="Severity: 1=low, 5=critical")
    severity_color: str = Field(..., description="Color: green, yellow, orange, red, dark-red")
    risk_factors: List[str] = Field(default_factory=list)
    legal_implications: str
    plain_language_explanation: str
    related_clauses: List[str] = Field(default_factory=list)
    compliance_flags: List[str] = Field(default_factory=list)
    position_in_document: PositionInDocument
    analysis_metadata: AnalysisMetadata
    qdrant_stored: bool = Field(default=False)
    user_id: Optional[str] = Field(default=None, description="User ID for data isolation")

class ClauseCreate(ClauseBase):
    """Schema for creating new clauses"""
    pass

class ClauseUpdate(BaseModel):
    """Schema for updating clauses"""
    clause_title: Optional[str] = None
    clause_type: Optional[str] = None
    severity_level: Optional[int] = None
    severity_color: Optional[str] = None
    risk_factors: Optional[List[str]] = None
    legal_implications: Optional[str] = None
    plain_language_explanation: Optional[str] = None
    related_clauses: Optional[List[str]] = None
    compliance_flags: Optional[List[str]] = None
    qdrant_stored: Optional[bool] = None

class Clause(ClauseBase):
    """Full clause schema with database ID"""
    id: Optional[str] = Field(default=None, alias="_id")

    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {
            ObjectId: str
        }

    @classmethod
    def from_mongo(cls, data: dict) -> 'Clause':
        """Create Clause instance from MongoDB document with proper ObjectId handling"""
        if '_id' in data and isinstance(data['_id'], ObjectId):
            data['_id'] = str(data['_id'])
        return cls(**data)

class ClauseInDB(Clause):
    """Clause as stored in database"""
    id: Optional[str] = Field(default=None, alias="_id")

    class Config:
        allow_population_by_field_name = True

# Severity level constants
SEVERITY_LEVELS = {
    1: "Informational - Standard boilerplate",
    2: "Low Risk - Minor implications",
    3: "Moderate Risk - Requires attention",
    4: "High Risk - Significant legal implications",
    5: "Critical Risk - Major financial/legal exposure"
}

# Color mapping for severity levels
SEVERITY_COLORS = {
    1: "#22C55E",  # Green
    2: "#84CC16",  # Light Green
    3: "#EAB308",  # Yellow
    4: "#F97316",  # Orange
    5: "#DC2626"   # Red
}

# Clause type categories
CLAUSE_TYPES = [
    "property_details",
    "payment",
    "termination",
    "liability",
    "confidentiality",
    "governing_law",
    "dispute_resolution",
    "force_majeure",
    "maintenance",
    "security_deposit",
    "insurance",
    "notices",
    "assignment",
    "severability",
    "entire_agreement",
    "amendment",
    "warranties",
    "indemnification",
    "intellectual_property",
    "data_protection",
    "other"
]
