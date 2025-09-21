"""
Main entry point for the Legal Document & Audio Summarizer API
This file allows running the application with 'uvicorn main:app'
"""

from app.main import app

# Re-export the FastAPI app instance for uvicorn
__all__ = ["app"]
