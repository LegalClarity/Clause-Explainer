"""
Health check router for monitoring API status
"""

import time
from datetime import datetime
from typing import Dict
from fastapi import APIRouter, Depends
from loguru import logger

from ..models.requests import HealthResponse
from ..services.database import db_service
from ..services.gemini_service import gemini_service
from ..services.document_service import document_service
from ..services.audio_service import audio_service
from ..config import settings

router = APIRouter(prefix="/health", tags=["health"])

# Track application start time
app_start_time = time.time()


@router.get("/", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint to verify API and service status
    """
    try:
        current_time = datetime.utcnow()
        uptime = time.time() - app_start_time
        
        # Check service statuses
        services = {}
        
        # Database status
        try:
            if db_service.client:
                await db_service.client.admin.command('ping')
                services["database"] = "healthy"
            else:
                services["database"] = "not_connected"
        except Exception as e:
            services["database"] = f"unhealthy: {str(e)}"
            logger.warning(f"Database health check failed: {e}")
        
        # Gemini service status
        try:
            if gemini_service.client:
                services["gemini_ai"] = "healthy"
            else:
                services["gemini_ai"] = "not_initialized"
        except Exception as e:
            services["gemini_ai"] = f"unhealthy: {str(e)}"
            logger.warning(f"Gemini service health check failed: {e}")
        
        # Document service status
        try:
            if document_service.document_ai_client:
                services["document_ai"] = "healthy"
            else:
                services["document_ai"] = "not_initialized"
        except Exception as e:
            services["document_ai"] = f"unhealthy: {str(e)}"
            logger.warning(f"Document service health check failed: {e}")
        
        # Audio service status
        try:
            if audio_service.speech_client:
                services["speech_to_text"] = "healthy"
            else:
                services["speech_to_text"] = "not_initialized"
        except Exception as e:
            services["speech_to_text"] = f"unhealthy: {str(e)}"
            logger.warning(f"Audio service health check failed: {e}")
        
        # Determine overall status
        unhealthy_services = [name for name, status in services.items() if "unhealthy" in status]
        if unhealthy_services:
            overall_status = "degraded"
        elif any("not_" in status for status in services.values()):
            overall_status = "partial"
        else:
            overall_status = "healthy"
        
        return HealthResponse(
            status=overall_status,
            timestamp=current_time,
            version="1.0.0",
            services=services,
            uptime_seconds=uptime
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            version="1.0.0",
            services={"error": str(e)},
            uptime_seconds=time.time() - app_start_time
        )


@router.get("/detailed", response_model=Dict)
async def detailed_health_check():
    """
    Detailed health check with system metrics and statistics
    """
    try:
        health_data = await health_check()
        
        # Add detailed information
        detailed_info = health_data.dict()
        
        # Database statistics
        try:
            db_stats = await db_service.get_database_stats()
            detailed_info["database_stats"] = db_stats
        except Exception as e:
            detailed_info["database_stats"] = {"error": str(e)}
        
        # System information
        import psutil
        import platform
        
        detailed_info["system_info"] = {
            "platform": platform.platform(),
            "python_version": platform.python_version(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage('/').percent
        }
        
        # Configuration info (non-sensitive)
        detailed_info["configuration"] = {
            "debug_mode": settings.debug_mode,
            "api_version": settings.api_version,
            "max_file_size_mb": settings.max_file_size_mb,
            "max_document_pages": settings.max_document_pages,
            "max_audio_duration_minutes": settings.max_audio_duration_minutes,
            "enable_caching": settings.enable_caching,
            "vertex_ai_region": settings.vertex_ai_region
        }
        
        return detailed_info
        
    except Exception as e:
        logger.error(f"Detailed health check failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@router.get("/services")
async def service_status():
    """
    Check individual service availability
    """
    services = {}
    
    # Test database connection
    try:
        if db_service.client:
            await db_service.client.admin.command('ping')
            services["database"] = {
                "status": "healthy",
                "response_time_ms": None  # Could measure actual response time
            }
        else:
            services["database"] = {
                "status": "not_connected",
                "error": "Database client not initialized"
            }
    except Exception as e:
        services["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Test other services similarly...
    # This would include actual connectivity tests to Google Cloud services
    
    return services


@router.get("/metrics")
async def get_metrics():
    """
    Get application metrics (for monitoring/alerting)
    """
    try:
        metrics = {
            "uptime_seconds": time.time() - app_start_time,
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
        
        # Add database metrics
        try:
            db_stats = await db_service.get_database_stats()
            metrics.update(db_stats)
        except Exception:
            pass
        
        # Add system metrics
        try:
            import psutil
            metrics.update({
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent
            })
        except Exception:
            pass
        
        return metrics
        
    except Exception as e:
        logger.error(f"Failed to get metrics: {e}")
        return {"error": str(e)}
