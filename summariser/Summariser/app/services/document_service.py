"""
Document processing service for legal document analysis
"""

import io
import time
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from fastapi import UploadFile, HTTPException
from google.cloud import documentai
from loguru import logger
import PyPDF2

from ..config import settings, SUPPORTED_DOCUMENT_TYPES
from ..models.schemas import DocumentSummary, DocumentSummaryDocument
from ..models.requests import DocumentSummarizeRequest
from ..services.database import db_service
from ..services.gemini_service import gemini_service
from ..utils.file_handler import FileHandler


class DocumentService:
    """Service for processing legal documents"""
    
    def __init__(self):
        self.document_ai_client = None
        self.processor_name = None
        self.file_handler = FileHandler()
        
    async def initialize(self):
        """Initialize the Document AI client"""
        try:
            self.document_ai_client = documentai.DocumentProcessorServiceClient()
            # You would set up a specific processor for legal documents
            self.processor_name = f"projects/{settings.google_cloud_project_id}/locations/{settings.vertex_ai_region}/processors/YOUR_PROCESSOR_ID"
            logger.info("Document service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize document service: {e}")
            # Continue without Document AI for now
            logger.warning("Continuing without Document AI - using fallback text extraction")
    
    async def process_document(self, file: UploadFile, request: DocumentSummarizeRequest) -> Tuple[DocumentSummary, bool, float]:
        """
        Process a legal document and return summary
        Returns: (summary, is_cached, processing_time)
        """
        start_time = time.time()
        
        try:
            # Read file content
            file_content = await file.read()
            file_hash = db_service.generate_file_hash(file_content)
            
            # Check for cached result
            cached_summary = await db_service.get_document_summary_by_hash(file_hash)
            if cached_summary:
                processing_time = time.time() - start_time
                return cached_summary.summary, True, processing_time
            
            # Validate file
            await self._validate_document_file(file, file_content)
            
            # Extract text from document
            extracted_text = await self._extract_text_from_document(file_content, file.content_type)
            
            if not extracted_text or len(extracted_text.strip()) < 100:
                raise HTTPException(
                    status_code=422,
                    detail="Document appears to be empty or contains insufficient text for analysis"
                )
            
            # Prepare options for Gemini analysis
            analysis_options = {
                'summary_length': request.summary_length,
                'include_financial_analysis': request.include_financial_analysis,
                'include_risk_assessment': request.include_risk_assessment,
                'language_preference': request.language_preference
            }
            
            # Analyze document with Gemini
            summary = await gemini_service.analyze_document(extracted_text, analysis_options)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Save to database if caching is enabled
            if settings.enable_caching:
                try:
                    summary_doc = DocumentSummaryDocument(
                        document_hash=file_hash,
                        filename=file.filename,
                        file_type=SUPPORTED_DOCUMENT_TYPES.get(file.content_type, 'unknown'),
                        file_size_bytes=len(file_content),
                        processed_timestamp=datetime.utcnow(),
                        processing_time_seconds=processing_time,
                        summary=summary
                    )
                    await db_service.save_document_summary(summary_doc)
                except Exception as e:
                    logger.warning(f"Failed to cache document summary: {e}")
            
            logger.info(f"Document processed successfully in {processing_time:.2f}s")
            return summary, False, processing_time
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing document: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process document: {str(e)}"
            )
    
    async def _validate_document_file(self, file: UploadFile, file_content: bytes):
        """Validate uploaded document file"""
        # Check file type
        if file.content_type not in SUPPORTED_DOCUMENT_TYPES:
            supported_types = ", ".join(SUPPORTED_DOCUMENT_TYPES.keys())
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file type. Supported types: {supported_types}"
            )
        
        # Check file size
        max_size_bytes = settings.max_file_size_mb * 1024 * 1024
        if len(file_content) > max_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {settings.max_file_size_mb}MB"
            )
        
        # Check if file is not empty
        if len(file_content) == 0:
            raise HTTPException(
                status_code=422,
                detail="Uploaded file is empty"
            )
        
        logger.info(f"Document validation passed: {file.filename} ({len(file_content)} bytes)")
    
    async def _extract_text_from_document(self, file_content: bytes, content_type: str) -> str:
        """Extract text from different document formats"""
        try:
            file_type = SUPPORTED_DOCUMENT_TYPES.get(content_type)
            
            if file_type == 'pdf':
                return await self._extract_text_from_pdf(file_content)
            elif file_type == 'txt':
                return file_content.decode('utf-8')
            elif file_type == 'docx':
                return await self._extract_text_from_docx(file_content)
            else:
                # Fallback: try Document AI if available
                if self.document_ai_client:
                    return await self._extract_text_with_document_ai(file_content)
                else:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Cannot process file type: {file_type}"
                    )
                    
        except Exception as e:
            logger.error(f"Error extracting text: {e}")
            raise HTTPException(
                status_code=422,
                detail=f"Failed to extract text from document: {str(e)}"
            )
    
    async def _extract_text_from_pdf(self, file_content: bytes) -> str:
        """Extract text from PDF using PyPDF2"""
        try:
            pdf_file = io.BytesIO(file_content)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            # Check page count
            num_pages = len(pdf_reader.pages)
            if num_pages > settings.max_document_pages:
                raise HTTPException(
                    status_code=422,
                    detail=f"Document too long. Maximum pages: {settings.max_document_pages}"
                )
            
            # Extract text from all pages
            text_content = []
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text_content.append(page.extract_text())
            
            extracted_text = "\n\n".join(text_content)
            
            # Clean up the text
            extracted_text = self._clean_extracted_text(extracted_text)
            
            logger.info(f"Extracted {len(extracted_text)} characters from {num_pages} page PDF")
            return extracted_text
            
        except Exception as e:
            logger.error(f"Error extracting PDF text: {e}")
            raise
    
    async def _extract_text_from_docx(self, file_content: bytes) -> str:
        """Extract text from DOCX files"""
        try:
            # This would require python-docx library
            # For now, we'll raise an error and suggest PDF or text format
            raise HTTPException(
                status_code=422,
                detail="DOCX processing not yet implemented. Please convert to PDF or plain text."
            )
        except Exception as e:
            logger.error(f"Error extracting DOCX text: {e}")
            raise
    
    async def _extract_text_with_document_ai(self, file_content: bytes) -> str:
        """Extract text using Google Cloud Document AI"""
        try:
            # Create the request
            request = documentai.ProcessRequest(
                name=self.processor_name,
                raw_document=documentai.RawDocument(
                    content=file_content,
                    mime_type="application/pdf"
                )
            )
            
            # Process the document
            def sync_process():
                return self.document_ai_client.process_document(request=request)
            
            # Run in thread pool to avoid blocking
            result = await asyncio.get_event_loop().run_in_executor(None, sync_process)
            
            # Extract text from result
            extracted_text = result.document.text
            
            # Clean up the text
            extracted_text = self._clean_extracted_text(extracted_text)
            
            logger.info(f"Extracted {len(extracted_text)} characters using Document AI")
            return extracted_text
            
        except Exception as e:
            logger.error(f"Error with Document AI: {e}")
            raise
    
    def _clean_extracted_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        if not text:
            return ""
        
        # Remove excessive whitespace
        import re
        text = re.sub(r'\s+', ' ', text)
        
        # Remove common OCR artifacts
        text = re.sub(r'[^\w\s\.\,\;\:\!\?\(\)\[\]\{\}\"\'\-]', '', text)
        
        # Normalize line breaks
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        return text.strip()
    
    async def validate_document_file(self, file: UploadFile) -> Dict[str, Any]:
        """Validate document file and return validation info"""
        try:
            file_content = await file.read()
            await file.seek(0)  # Reset file pointer
            
            validation_result = {
                'valid': True,
                'file_type': SUPPORTED_DOCUMENT_TYPES.get(file.content_type, 'unknown'),
                'file_size_bytes': len(file_content),
                'warnings': [],
                'errors': []
            }
            
            # File type validation
            if file.content_type not in SUPPORTED_DOCUMENT_TYPES:
                validation_result['valid'] = False
                validation_result['errors'].append(f"Unsupported file type: {file.content_type}")
            
            # File size validation
            max_size_bytes = settings.max_file_size_mb * 1024 * 1024
            if len(file_content) > max_size_bytes:
                validation_result['valid'] = False
                validation_result['errors'].append(f"File too large: {len(file_content)} bytes (max: {max_size_bytes})")
            
            # Empty file check
            if len(file_content) == 0:
                validation_result['valid'] = False
                validation_result['errors'].append("File is empty")
            
            # Estimate processing time
            if validation_result['valid']:
                estimated_time = self._estimate_processing_time(len(file_content), file.content_type)
                validation_result['estimated_processing_time'] = estimated_time
            
            return validation_result
            
        except Exception as e:
            return {
                'valid': False,
                'file_type': 'unknown',
                'file_size_bytes': 0,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': []
            }
    
    def _estimate_processing_time(self, file_size: int, content_type: str) -> float:
        """Estimate processing time based on file size and type"""
        # Base processing time in seconds
        base_time = 5.0
        
        # Add time based on file size (roughly 1 second per MB)
        size_mb = file_size / (1024 * 1024)
        size_time = size_mb * 1.0
        
        # Add time based on file type
        type_multiplier = {
            'application/pdf': 1.5,
            'text/plain': 0.5,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 2.0
        }
        
        multiplier = type_multiplier.get(content_type, 1.0)
        
        return (base_time + size_time) * multiplier


# Global document service instance
document_service = DocumentService()
