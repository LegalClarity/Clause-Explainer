from pydantic_settings import BaseSettings
from pydantic import Field, SecretStr, field_validator
from typing import Optional, List
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # FastAPI Settings
    app_name: str = "Clause Explainer Timeline API"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")

    # Server Settings
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")

    # MongoDB Settings
    mongodb_url: str = Field(env="MONGODB_URL")
    mongodb_database: str = Field(default="clause_explainer", env="MONGODB_DATABASE")

    # Qdrant Settings
    qdrant_host: str = Field(env="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, env="QDRANT_PORT")
    qdrant_api_key: Optional[SecretStr] = Field(default=None, env="QDRANT_API_KEY")

    # AI API Settings
    openai_api_key: Optional[SecretStr] = Field(default=None, env="OPENAI_API_KEY")
    google_api_key: Optional[SecretStr] = Field(default=None, env="GOOGLE_API_KEY")
    ai_model_preference: str = Field(default="openai", env="AI_MODEL_PREFERENCE")  # "openai" or "google"

    # Document Processing Settings
    max_file_size: int = Field(default=50 * 1024 * 1024, env="MAX_FILE_SIZE")  # 50MB
    allowed_file_types: List[str] = ["application/pdf"]

    # Vector Settings
    embedding_model: str = Field(default="sentence-transformers/all-MiniLM-L6-v2", env="EMBEDDING_MODEL")
    embedding_dimension: int = Field(default=384, env="EMBEDDING_DIMENSION")

    # Processing Settings
    max_processing_time: int = Field(default=300, env="MAX_PROCESSING_TIME")  # 5 minutes
    batch_size: int = Field(default=10, env="BATCH_SIZE")

    # Security Settings
    cors_origins: List[str] = []


    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Allow extra fields from environment variables

# Global settings instance
settings = Settings()
