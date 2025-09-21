"""
Legal Document & Audio Summarizer FastAPI Application

This is the main FastAPI application that provides intelligent summarization
of legal documents and audio recordings using Google Cloud AI services.
"""

# Load environment variables FIRST before any other imports
from dotenv import load_dotenv
load_dotenv()

import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger
import uvicorn

from .config import settings
from .routers import health_router, documents_router, audio_router
from .services import db_service, document_service, gemini_service, tts_service
from .models.requests import ErrorResponse


# Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events
    """
    # Startup
    logger.info("Starting Legal Summarizer API...")
    
    try:
        # Initialize services
        logger.info("🚀 Starting service initialization...")

        # Initialize Database
        logger.info("🔄 Initializing database service...")
        await db_service.connect()
        logger.info("✅ Database service initialized")

        # Initialize Document Service
        logger.info("🔄 Initializing document service...")
        await document_service.initialize()
        logger.info("✅ Document service initialized")

        # Initialize Gemini Service
        logger.info("🔄 Initializing Gemini AI service...")
        await gemini_service.initialize()

        # Initialize TTS Service
        logger.info("🔄 Initializing Text-to-Speech service...")
        await tts_service.initialize()

        # Print comprehensive status summary
        logger.info("🎉 SERVICE INITIALIZATION COMPLETE!")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("📊 SERVICE STATUS SUMMARY:")
        logger.info(f"   🗄️  Database: ✅ Connected")
        logger.info(f"   📄 Documents: ✅ Ready")
        logger.info(f"   🤖 Gemini AI: {'✅ Working' if not getattr(gemini_service, 'use_mock', True) else '❌ Mock Mode (API key issue)'}")
        logger.info(f"   🔊 Text-to-Speech: {'✅ Working' if not getattr(tts_service, 'use_mock', True) else '❌ Mock Mode (API key issue)'}")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        gemini_mock = getattr(gemini_service, 'use_mock', True)
        tts_mock = getattr(tts_service, 'use_mock', True)

        if gemini_mock or tts_mock:
            logger.warning("⚠️  SOME SERVICES ARE IN MOCK MODE:")
            if gemini_mock:
                logger.warning("   ❌ Gemini: Check GEMINI_API_KEY and project permissions")
            if tts_mock:
                logger.warning("   ❌ TTS: Check API key and Google Cloud project setup")
            logger.warning("   📖 See: https://cloud.google.com/text-to-speech/docs/quickstart")

        logger.info("🎯 API is ready to process requests!")
        
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        # Continue startup even if some services fail
    
    yield
    
    # Shutdown
    logger.info("Shutting down Legal Summarizer API...")
    
    try:
        await db_service.disconnect()
        logger.info("Services disconnected successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="Legal Document & Audio Summarizer API",
    description="""
    A comprehensive FastAPI backend service that provides intelligent summarization
    and speech conversion of legal documents using Google Cloud AI services.

    ## Features

    * **Document Analysis**: Upload PDF files for comprehensive legal analysis
    * **PDF-to-Speech Conversion**: Convert legal documents to professional audio narration
    * **AI-Powered Insights**: Advanced analysis using Google Cloud Gemini AI
    * **Legal Risk Assessment**: Identify and categorize legal risks with mitigation strategies
    * **Financial Impact Analysis**: Assess potential costs and liabilities
    * **Text-to-Speech**: High-quality speech synthesis using Gemini TTS API
    * **Professional Narration**: Legal document summaries narrated by AI voices
    * **Caching**: Intelligent caching to avoid reprocessing identical files

    ## Supported File Types

    **Documents**: PDF (up to 50 pages, 100MB) for speech conversion
    **Output**: MP3 audio files with professional narration

    ## Authentication

    This API currently operates without authentication for development purposes.
    In production, implement proper authentication and rate limiting.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure logging
logger.add(
    "logs/api.log",
    rotation="1 day",
    retention="30 days",
    level=settings.log_level,
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}"
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trust only specific hosts in production
if not settings.debug_mode:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["localhost", "127.0.0.1", "*.yourdomain.com"]
    )


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID to each request for tracking"""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    start_time = time.time()
    
    # Add request ID to logger context
    with logger.contextualize(request_id=request_id):
        logger.info(f"Request started: {request.method} {request.url}")
        
        response = await call_next(request)
        
        process_time = time.time() - start_time
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        logger.info(
            f"Request completed: {request.method} {request.url} "
            f"(status: {response.status_code}, time: {process_time:.3f}s)"
        )
    
    return response


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent error format"""
    request_id = getattr(request.state, 'request_id', None)
    
    error_response = ErrorResponse(        error=exc.__class__.__name__,        message=str(exc.detail),
        timestamp=datetime.utcnow(),
        request_id=request_id
    )
    
    logger.warning(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode='json')
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle request validation errors"""
    request_id = getattr(request.state, 'request_id', None)
    
    error_details = []
    for error in exc.errors():
        error_details.append({
            "field": " -> ".join(str(x) for x in error["loc"]),
            "message": error["msg"],
            "type": error["type"]
        })
    
    error_response = ErrorResponse(
        error="ValidationError",
        message="Request validation failed",
        details={"validation_errors": error_details},        timestamp=datetime.utcnow(),
        request_id=request_id    )
    
    logger.warning(f"Validation Error: {error_details}")
    
    return JSONResponse(
        status_code=422,
        content=error_response.model_dump(mode='json')
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    request_id = getattr(request.state, 'request_id', None)
    
    error_response = ErrorResponse(        error="InternalServerError",
        message="An unexpected error occurred",
        details={"error_type": exc.__class__.__name__} if settings.debug_mode else None,
        timestamp=datetime.utcnow(),
        request_id=request_id
    )
    
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(mode='json')
    )


# Include routers
app.include_router(health_router)
app.include_router(documents_router)
app.include_router(audio_router)


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint with API information
    """
    return {
        "name": "Legal Document PDF-to-Speech API",
        "version": "1.0.0",
        "description": "AI-powered legal document analysis and speech conversion service",
        "docs_url": "/docs",
        "health_check": "/health",
        "endpoints": {
            "documents": "/documents/summarize",
            "pdf_to_speech": "/audio/pdf-to-speech",
            "health": "/health"
        },
        "supported_formats": {
            "input": ["PDF documents"],
            "output": ["MP3 audio narration"]
        },
        "features": [
            "PDF document analysis",
            "AI-powered legal summarization",
            "Professional text-to-speech conversion",
            "Legal risk assessment",
            "Financial impact analysis",
            "Audio download and streaming"
        ]
    }


@app.get("/api", tags=["api"])
async def api_info():
    """
    API information and available endpoints
    """
    return {
        "api_version": settings.api_version,
        "endpoints": {
            "documents": {
                "summarize": "/documents/summarize"
            },
            "pdf_to_speech": {
                "convert_and_download": "/audio/pdf-to-speech"
            },
            "health": {
                "status": "/health",
                "detailed": "/health/detailed",
                "services": "/health/services",
                "metrics": "/health/metrics"
            }
        },
        "limits": {
            "max_file_size_mb": settings.max_file_size_mb,
            "max_document_pages": settings.max_document_pages,
            "processing_timeout_seconds": settings.processing_timeout_seconds
        }
    }


# Development server
if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug_mode,
        log_level=settings.log_level.lower(),
        access_log=True
    )
