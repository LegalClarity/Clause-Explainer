"""
Configuration settings for the Legal Summarizer API
"""

# Load environment variables FIRST before any other imports
from dotenv import load_dotenv
load_dotenv()

import os
from typing import Optional

try:
    from pydantic_settings import BaseSettings
    from pydantic import Field
except ImportError:
    from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # API Configuration
    api_version: str = Field(default="v1", env="API_VERSION")
    debug_mode: bool = Field(default=False, env="DEBUG_MODE")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")

    # Google Cloud Configuration
    google_cloud_project_id: Optional[str] = None
    google_application_credentials: Optional[str] = None
    vertex_ai_region: str = "asia-south1"
    gemini_api_key: Optional[str] = None

    # MongoDB Configuration
    mongodb_connection_string: str = Field(..., env="MONGODB_CONNECTION_STRING")
    mongodb_database_name: str = Field(default="legal_summarizer", env="MONGODB_DATABASE_NAME")

    # File Storage Configuration
    upload_directory: str = Field(default="/tmp/uploads", env="UPLOAD_DIRECTORY")
    max_file_size_mb: int = Field(default=100, env="MAX_FILE_SIZE_MB")

    # Processing Configuration
    max_document_pages: int = Field(default=50, env="MAX_DOCUMENT_PAGES")
    max_audio_duration_minutes: int = Field(default=180, env="MAX_AUDIO_DURATION_MINUTES")
    processing_timeout_seconds: int = Field(default=1800, env="PROCESSING_TIMEOUT_SECONDS")

    # Cache Configuration
    enable_caching: bool = Field(default=True, env="ENABLE_CACHING")
    cache_ttl_hours: int = Field(default=24, env="CACHE_TTL_HOURS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields from environment

    def __init__(self, **data):
        super().__init__(**data)

        # Manually set Google Cloud fields from environment variables
        # since pydantic env mapping is not working properly
        if not self.google_cloud_project_id:
            self.google_cloud_project_id = os.getenv("GOOGLE_PROJECT_ID") or \
                                         os.getenv("GOOGLE_CLOUD_PROJECT") or \
                                         os.getenv("GOOGLE_CLOUD_PROJECT_ID")

        if not self.google_application_credentials:
            self.google_application_credentials = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

        if self.vertex_ai_region == "asia-south1":  # Only override if it's the default
            region = os.getenv("GOOGLE_REGION") or \
                    os.getenv("GOOGLE_CLOUD_REGION") or \
                    os.getenv("VERTEX_AI_REGION")
            if region:
                self.vertex_ai_region = region

        if not self.gemini_api_key:
            self.gemini_api_key = os.getenv("GEMINI_API_KEY") or \
                                 os.getenv("GOOGLE_API_KEY")


# Global settings instance
settings = Settings()

# Supported file types
SUPPORTED_DOCUMENT_TYPES = {
    'application/pdf': 'pdf',
    'text/plain': 'txt',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx'
}

SUPPORTED_AUDIO_TYPES = {
    'audio/mpeg': 'mp3',
    'audio/wav': 'wav',
    'audio/x-wav': 'wav',
    'audio/mp4': 'm4a',
    'audio/x-m4a': 'm4a'
}

# Legal framework types
LEGAL_FRAMEWORK_TYPES = [
    "statute",
    "regulation",
    "case_law",
    "constitutional",
    "administrative",
    "procedural"
]

# Risk severity levels
RISK_SEVERITY_LEVELS = [
    "low",
    "medium", 
    "high",
    "critical"
]

# Audio session types
AUDIO_SESSION_TYPES = [
    "hearing",
    "deposition", 
    "consultation",
    "meeting",
    "interview",
    "general"
]

# Speaker roles
SPEAKER_ROLES = [
    "judge",
    "attorney",
    "witness", 
    "plaintiff",
    "defendant",
    "court_reporter",
    "bailiff",
    "expert_witness",
    "unknown"
]
