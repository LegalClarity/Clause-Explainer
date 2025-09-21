"""
Combined FastAPI Application for Clause Explainer and Legal Summarizer APIs

This application combines two legal document processing services:
1. Clause Explainer Timeline API - Document clause analysis and timeline generation
2. Legal Document & Audio Summarizer API - Document summarization and speech conversion
"""

import time
import logging
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from loguru import logger
import uvicorn

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Import clause_exp components
from clause_exp.app.config.settings import settings as clause_settings
from clause_exp.app.api.router import router as clause_router
from clause_exp.app.services import mongodb_service as clause_mongodb, qdrant_service as clause_qdrant

# Import summariser components
from summariser.Summariser.app.config import settings as summariser_settings
from summariser.Summariser.app.routers import health_router, documents_router, audio_router

# Create a combined summariser router
from fastapi import APIRouter
summariser_router = APIRouter(prefix="/summariser", tags=["summariser"])

# Include all summariser endpoints in the combined router
summariser_router.include_router(health_router)
summariser_router.include_router(documents_router)
summariser_router.include_router(audio_router)

from summariser.Summariser.app.services import db_service, document_service, gemini_service, tts_service
from summariser.Summariser.app.models.requests import ErrorResponse


# Combined lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Combined application lifespan manager for startup and shutdown events
    """
    # Startup
    logger.info("🚀 Starting Combined Legal Document Processing API...")

    try:
        # Initialize Clause Explainer services
        logger.info("🔄 Initializing Clause Explainer services...")

        # Initialize MongoDB connection for clause_exp
        await clause_mongodb.connect()
        logger.info("✅ Clause Explainer MongoDB connected")

        # Initialize and test Qdrant connection
        await clause_qdrant.initialize()
        collections = clause_qdrant.client.get_collections()
        logger.info(f"✅ Clause Explainer Qdrant connected, found {len(collections.collections)} collections")

        # Initialize Summariser services
        logger.info("🔄 Initializing Legal Summarizer services...")

        # Initialize Database for summariser
        await db_service.connect()
        logger.info("✅ Legal Summarizer database initialized")

        # Initialize Document Service
        await document_service.initialize()
        logger.info("✅ Document service initialized")

        # Initialize Gemini Service
        await gemini_service.initialize()

        # Initialize TTS Service
        await tts_service.initialize()

        # Print comprehensive status summary
        logger.info("🎉 ALL SERVICES INITIALIZATION COMPLETE!")
        logger.info("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info("📊 SERVICE STATUS SUMMARY:")
        logger.info("   🗄️  Clause Explainer DB: ✅ Connected")
        logger.info("   🔍 Clause Explainer Qdrant: ✅ Connected")
        logger.info("   🗄️  Legal Summarizer DB: ✅ Connected")
        logger.info("   📄 Documents: ✅ Ready")
        logger.info(f"   🤖 Gemini AI: {'✅ Working' if not getattr(gemini_service, 'use_mock', True) else '❌ Mock Mode'}")
        logger.info(f"   🔊 Text-to-Speech: {'✅ Working' if not getattr(tts_service, 'use_mock', True) else '❌ Mock Mode'}")
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

        logger.info("🎯 Combined API is ready to process requests!")

    except Exception as e:
        logger.error(f"❌ Failed to initialize services: {e}")
        # Continue startup even if some services fail

    yield

    # Shutdown
    logger.info("Shutting down Combined Legal Document Processing API...")

    try:
        await clause_mongodb.disconnect()
        await db_service.disconnect()
        logger.info("✅ All services disconnected successfully")
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title="Combined Legal Document Processing API",
    description="""
    A comprehensive FastAPI backend service that combines two legal document processing APIs:

    ## Clause Explainer Timeline API
    * **Document Analysis**: Upload and analyze legal documents to extract clauses
    * **Timeline Generation**: Create visual timelines of document clauses
    * **AI-Powered Insights**: Advanced analysis using AI services
    * **Risk Assessment**: Identify and categorize legal risks

    ## Legal Document & Audio Summarizer API
    * **Document Summarization**: Intelligent summarization of legal documents
    * **PDF-to-Speech Conversion**: Convert legal documents to professional audio narration
    * **AI-Powered Analysis**: Advanced analysis using Google Cloud Gemini AI
    * **Legal Risk Assessment**: Assess potential costs and liabilities

    ## Supported File Types
    **Documents**: PDF, DOCX, TXT files
    **Output**: MP3 audio files with professional narration

    ## Authentication
    This API currently operates without authentication for development purposes.
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configure logging
logger.add(
    "logs/combined_api.log",
    rotation="1 day",
    retention="30 days",
    level="INFO",
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
if not getattr(summariser_settings, 'debug_mode', True):
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

    error_response = ErrorResponse(
        error=exc.__class__.__name__,
        message=str(exc.detail),
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
        details={"validation_errors": error_details},
        timestamp=datetime.utcnow(),
        request_id=request_id
    )

    logger.warning(f"Validation Error: {error_details}")

    return JSONResponse(
        status_code=422,
        content=error_response.model_dump(mode='json')
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    request_id = getattr(request.state, 'request_id', None)

    error_response = ErrorResponse(
        error="InternalServerError",
        message="An unexpected error occurred",
        details={"error_type": exc.__class__.__name__} if getattr(summariser_settings, 'debug_mode', False) else None,
        timestamp=datetime.utcnow(),
        request_id=request_id
    )

    logger.error(f"Unexpected error: {exc}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(mode='json')
    )


# Include routers
app.include_router(
    clause_router,
    prefix="/clause_exp",
    tags=["clause_explainer"]
)

# Combined summariser router
app.include_router(summariser_router)


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint with API information
    """
    return {
        "name": "Combined Legal Document Processing API",
        "version": "1.0.0",
        "description": "Integrated legal document analysis, summarization, and speech conversion service",
        "apis": {
            "clause_explainer": {
                "description": "Document clause analysis and timeline generation",
                "prefix": "/clause_exp",
                "docs": "/docs",
                "endpoints": {
                    "analyze_document": "/clause_exp/documents/analyze",
                    "document_status": "/clause_exp/documents/{document_id}/status",
                    "clause_details": "/clause_exp/documents/{document_id}/clauses/{clause_id}/details",
                    "rag_query": "/clause_exp/rag/query"
                }
            },
            "summariser": {
                "description": "Document summarization and speech conversion",
                "prefix": "/summariser",
                "docs": "/docs",
                "endpoints": {
                    "health": "/summariser/health",
                    "summarize_document": "/summariser/documents/summarize",
                    "pdf_to_speech": "/summariser/audio/pdf-to-speech"
                }
            }
        },
        "docs_url": "/docs",
        "health_check": "/health"
    }


# Combined health check endpoint
@app.get("/health", tags=["health"])
async def combined_health_check():
    """Combined health check for all services"""
    health_status = {
        "status": "healthy",
        "timestamp": time.time(),
        "version": "1.0.0",
        "services": {}
    }

    try:
        # Clause Explainer health checks
        health_status["services"]["clause_explainer"] = {
            "mongodb": "connected" if clause_mongodb.client else "disconnected",
            "qdrant": f"connected ({len(clause_qdrant.client.get_collections().collections)} collections)"
        }
    except Exception as e:
        health_status["services"]["clause_explainer"] = {"error": str(e)}

    try:
        # Summariser health checks
        health_status["services"]["summariser"] = {
            "database": "connected" if db_service.client else "disconnected",
            "gemini": "working" if not getattr(gemini_service, 'use_mock', True) else "mock_mode",
            "tts": "working" if not getattr(tts_service, 'use_mock', True) else "mock_mode"
        }
    except Exception as e:
        health_status["services"]["summariser"] = {"error": str(e)}

    return health_status


# Development server
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )
