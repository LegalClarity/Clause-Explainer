"""
Routers package initialization
"""

from .health import router as health_router
from .documents import router as documents_router  
from .audio import router as audio_router

__all__ = [
    "health_router",
    "documents_router", 
    "audio_router"
]
