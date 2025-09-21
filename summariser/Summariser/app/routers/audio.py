"""
PDF-to-Speech conversion router for legal document summarization and narration
"""

import time
import tempfile
import os
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from loguru import logger

# No request/response models needed since we return audio file directly
from ..services.document_service import document_service
from ..services.gemini_service import gemini_service
from ..services.tts_service import tts_service
from ..utils.validators import RequestValidator, BusinessLogicValidator
from ..utils.file_handler import FileValidator
from ..config import settings, SUPPORTED_DOCUMENT_TYPES

router = APIRouter(prefix="/audio", tags=["audio"])


@router.post("/pdf-to-speech")
async def convert_pdf_to_speech(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    document_title: str = Form("Legal Document"),
    summary_length: str = Form("comprehensive"),
    voice_name: str = Form("Charon"),
    model_name: str = Form("gemini-2.5-pro-preview-tts"),
    speaking_rate: float = Form(1.0),
    pitch: float = Form(0.0)
):
    """
    Convert a PDF legal document to speech narration and return audio file directly.

    This endpoint:
    1. Extracts text from the uploaded PDF
    2. Generates a comprehensive summary using AI
    3. Converts the summary to speech using Gemini TTS
    4. Returns the audio file directly for download

    The output is a downloadable MP3 file containing the narrated summary.
    """
    request_start_time = time.time()
    audio_filepath = None

    try:
        logger.info("=== PDF-TO-SPEECH CONVERSION STARTED ===")
        logger.info(f"Request parameters: title='{document_title}', summary_length='{summary_length}', voice='{voice_name}', model='{model_name}'")

        # Validate request parameters
        if not RequestValidator.validate_summary_length(summary_length):
            logger.error(f"Invalid summary_length: {summary_length}")
            raise HTTPException(
                status_code=422,
                detail="Invalid summary_length. Must be 'brief', 'standard', or 'comprehensive'"
            )

        if not document_title or len(document_title.strip()) == 0:
            logger.error("Document title is empty")
            raise HTTPException(
                status_code=422,
                detail="Document title cannot be empty"
            )

        # Validate filename
        filename_validation = RequestValidator.validate_file_name(file.filename)
        if not filename_validation['valid']:
            logger.warning(f"Filename validation warnings: {filename_validation['warnings']}")

        logger.info(f"Uploaded file: {file.filename}, content_type: {file.content_type}")

        # Validate file as document (PDF)
        file_validation = await FileValidator.validate_upload(file, 'document')
        if not file_validation['valid']:
            logger.error(f"File validation failed: {file_validation['errors']}")
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "FileValidationError",
                    "message": "File validation failed",
                    "errors": file_validation['errors'],
                    "warnings": file_validation.get('warnings', [])
                }
            )

        # Check if it's a PDF
        if file.content_type != 'application/pdf':
            logger.error(f"Unsupported file type: {file.content_type}")
            raise HTTPException(
                status_code=422,
                detail="Only PDF files are supported for speech conversion. Please upload a PDF document."
            )

        # Business logic validation
        file_info = file_validation['info']
        business_validation = BusinessLogicValidator.validate_processing_limits(
            file_info['size_bytes'],
            SUPPORTED_DOCUMENT_TYPES.get(file.content_type, 'unknown')
        )

        if not business_validation['valid']:
            logger.error(f"Business logic validation failed: {business_validation['errors']}")
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
            logger.warning(f"Processing warnings: {all_warnings}")

        logger.info(f"Starting PDF-to-speech conversion: {file.filename} ({file_info['size_formatted']})")
        logger.info("Step 1: Reading file content")

        # Read file content
        file_content = await file.read()
        logger.info(f"File content read: {len(file_content)} bytes")

        logger.info("Step 2: Extracting text from PDF")
        # Extract text from PDF
        extracted_text = await document_service._extract_text_from_pdf(file_content)
        logger.info(f"Text extracted: {len(extracted_text)} characters")

        if not extracted_text or len(extracted_text.strip()) < 100:
            logger.error(f"Insufficient text extracted: {len(extracted_text)} characters")
            raise HTTPException(
                status_code=422,
                detail="PDF appears to be empty or contains insufficient text for analysis"
            )

        logger.info("Step 3: Preparing analysis options")
        # Prepare options for Gemini analysis
        analysis_options = {
            'summary_length': summary_length,
            'include_financial_analysis': True,
            'include_risk_assessment': True,
            'language_preference': 'en'
        }
        logger.info(f"Analysis options: {analysis_options}")

        logger.info("Step 4: Generating AI summary")
        # Generate summary using Gemini
        document_summary = await gemini_service.analyze_document(extracted_text, analysis_options)
        logger.info("AI summary generated successfully")

        # Extract the executive summary text for TTS
        summary_text = document_summary.executive_summary
        if not summary_text or len(summary_text.strip()) < 50:
            logger.warning("Executive summary too short, using fallback from key takeaways")
            summary_text = "Key points from the document: " + ". ".join(document_summary.key_takeaways[:5])

        logger.info(f"Summary text length: {len(summary_text)} characters")
        logger.info(f"Summary text preview: {summary_text[:200]}...")

        # Generate audio file path
        audio_filename = f"legal_summary_{int(time.time())}_{filename_validation['sanitized'].replace('.pdf', '')}.mp3"
        audio_filepath = os.path.join(tempfile.gettempdir(), audio_filename)
        logger.info(f"Audio file path: {audio_filepath}")

        logger.info("Step 5: Converting summary to speech")
        # Convert summary to speech using Gemini TTS
        logger.info(f"TTS parameters: voice='{voice_name}', model='{model_name}', rate={speaking_rate}, pitch={pitch}")
        final_audio_path = await tts_service.synthesize_document_summary(
            summary_text=summary_text,
            document_title=document_title,
            output_filepath=audio_filepath,
            voice_name=voice_name,
            model_name=model_name,
            speaking_rate=speaking_rate,
            pitch=pitch
        )
        logger.info(f"TTS conversion completed: {final_audio_path}")

        # Validate that audio file was created and has content
        if not os.path.exists(final_audio_path):
            logger.error(f"Audio file was not created: {final_audio_path}")
            raise HTTPException(
                status_code=500,
                detail="Audio file was not created successfully"
            )

        file_size = os.path.getsize(final_audio_path)
        logger.info(f"Audio file size: {file_size} bytes")

        if file_size == 0:
            logger.error("Audio file is empty")
            raise HTTPException(
                status_code=500,
                detail="Generated audio file is empty"
            )

        # Calculate audio duration (rough estimation)
        word_count = len(summary_text.split())
        estimated_audio_duration = word_count * 0.3  # ~0.3 seconds per word at normal speaking rate

        # Calculate total processing time
        processing_time = time.time() - request_start_time

        logger.info("Step 6: Preparing response")
        logger.info(f"Processing completed in {processing_time:.2f}s")
        logger.info(f"Estimated audio duration: {estimated_audio_duration:.1f}s")

        # Create download filename
        download_filename = f"{document_title.replace(' ', '_')}_summary.mp3"
        logger.info(f"Download filename: {download_filename}")

        # Return audio file directly
        logger.info("=== PDF-TO-SPEECH CONVERSION COMPLETED SUCCESSFULLY ===")
        return FileResponse(
            path=final_audio_path,
            media_type="audio/mpeg",
            filename=download_filename,
            headers={
                "X-Document-Title": document_title,
                "X-File-Type": "pdf",
                "X-File-Size-Bytes": str(len(file_content)),
                "X-Extracted-Text-Length": str(len(extracted_text)),
                "X-Summary-Length": str(len(summary_text)),
                "X-Audio-Duration-Seconds": str(estimated_audio_duration),
                "X-Processing-Time-Seconds": str(processing_time),
                "X-Confidence-Score": str(document_summary.confidence_score),
                "X-Model-Name": model_name,
                "X-Voice-Name": voice_name
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("=== PDF-TO-SPEECH CONVERSION FAILED ===")
        logger.error(f"Unexpected error: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

        # Clean up audio file if it exists
        if audio_filepath and os.path.exists(audio_filepath):
            try:
                os.remove(audio_filepath)
                logger.info(f"Cleaned up audio file: {audio_filepath}")
            except Exception as cleanup_error:
                logger.error(f"Failed to clean up audio file: {cleanup_error}")

        raise HTTPException(
            status_code=500,
            detail={
                "error": "InternalServerError",
                "message": "An unexpected error occurred during PDF-to-speech conversion",
                "details": {
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            }
        )




