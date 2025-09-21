"""
Document processing router for legal document summarization
"""

import time
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from loguru import logger

from ..models.requests import DocumentSummarizeRequest, DocumentSummaryResponse, FileValidationResponse, ErrorResponse
from ..services.document_service import document_service
from ..utils.validators import RequestValidator, SecurityValidator, BusinessLogicValidator
from ..utils.file_handler import FileValidator
from ..config import SUPPORTED_DOCUMENT_TYPES

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/summarize", response_model=DocumentSummaryResponse)
async def summarize_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    include_financial_analysis: bool = Form(True),
    include_risk_assessment: bool = Form(True),
    summary_length: str = Form("comprehensive"),
    language_preference: str = Form("en")
):
    """
    Upload and immediately process a legal document for comprehensive summarization.
    
    This endpoint handles PDF, TXT, and DOCX files and returns:
    - Key takeaways and legal implications
    - Risk assessment with severity levels
    - Legal framework analysis
    - Financial implications
    - Executive summary
    
    The processing is done synchronously and returns the complete analysis.
    """
    request_start_time = time.time()
    
    try:
        # Validate request parameters
        if not RequestValidator.validate_summary_length(summary_length):
            raise HTTPException(
                status_code=422,
                detail="Invalid summary_length. Must be 'brief', 'standard', or 'comprehensive'"
            )
        
        if not RequestValidator.validate_language_code(language_preference):
            raise HTTPException(
                status_code=422,
                detail="Invalid language_preference. Must be valid language code (e.g., 'en', 'es')"
            )
        
        # Validate filename
        filename_validation = RequestValidator.validate_file_name(file.filename)
        if not filename_validation['valid']:
            logger.warning(f"Filename validation warnings: {filename_validation['warnings']}")
        
        # Comprehensive file validation
        file_validation = await FileValidator.validate_upload(file, 'document')
        if not file_validation['valid']:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "FileValidationError",
                    "message": "File validation failed",
                    "errors": file_validation['errors'],
                    "warnings": file_validation.get('warnings', [])
                }
            )
        
        # Business logic validation
        file_info = file_validation['info']
        business_validation = BusinessLogicValidator.validate_processing_limits(
            file_info['size_bytes'], 
            SUPPORTED_DOCUMENT_TYPES.get(file.content_type, 'unknown')
        )
        
        if not business_validation['valid']:
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "ProcessingLimitExceeded",
                    "message": "File exceeds processing limits",
                    "errors": business_validation['errors']
                }
            )
        
        # Log warnings if any
        all_warnings = file_validation.get('warnings', []) + business_validation.get('warnings', [])
        if all_warnings:
            logger.warning(f"Processing warnings for {file.filename}: {all_warnings}")
        
        # Create request object
        request_obj = DocumentSummarizeRequest(
            include_financial_analysis=include_financial_analysis,
            include_risk_assessment=include_risk_assessment,
            summary_length=summary_length,
            language_preference=language_preference
        )
        
        logger.info(f"Starting document processing: {file.filename} ({file_info['size_formatted']})")
        
        # Process document
        summary, is_cached, processing_time = await document_service.process_document(file, request_obj)
        
        # Calculate total request time
        total_time = time.time() - request_start_time
        
        # Create response
        response = DocumentSummaryResponse(
            filename=filename_validation['sanitized'],
            file_type=SUPPORTED_DOCUMENT_TYPES.get(file.content_type, 'unknown'),
            file_size_bytes=file_info['size_bytes'],
            summary=summary,
            confidence_score=summary.confidence_score,
            processing_time_seconds=processing_time,
            processed_at=datetime.utcnow(),
            cached_result=is_cached
        )
        
        # Log successful processing
        cache_status = "cached" if is_cached else "processed"
        logger.info(
            f"Document {cache_status} successfully: {file.filename} "
            f"(processing: {processing_time:.2f}s, total: {total_time:.2f}s)"
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing document {file.filename}: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalServerError",
                "message": "An unexpected error occurred during document processing",
                "details": {"error_type": type(e).__name__}
            }
        )


