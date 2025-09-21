"""
File handling utilities for the Legal Summarizer application
"""

import os
import tempfile
import hashlib
import mimetypes
from typing import Optional, Dict, Any, BinaryIO
from pathlib import Path
from fastapi import UploadFile, HTTPException
from loguru import logger

from ..config import settings, SUPPORTED_DOCUMENT_TYPES, SUPPORTED_AUDIO_TYPES


class FileHandler:
    """Utility class for file operations"""
    
    def __init__(self):
        self.temp_dir = settings.upload_directory
        self._ensure_temp_directory()
    
    def _ensure_temp_directory(self):
        """Ensure temporary directory exists"""
        try:
            Path(self.temp_dir).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logger.warning(f"Could not create temp directory {self.temp_dir}: {e}")
            self.temp_dir = tempfile.gettempdir()
    
    @staticmethod
    def generate_file_hash(content: bytes, algorithm: str = 'sha256') -> str:
        """Generate hash for file content"""
        if algorithm == 'sha256':
            return hashlib.sha256(content).hexdigest()
        elif algorithm == 'md5':
            return hashlib.md5(content).hexdigest()
        else:
            raise ValueError(f"Unsupported hash algorithm: {algorithm}")
    
    @staticmethod
    def detect_file_type(filename: str, content: bytes) -> Optional[str]:
        """Detect file type from filename and content"""
        # First try by MIME type detection
        mime_type, _ = mimetypes.guess_type(filename)
        
        if mime_type:
            return mime_type
        
        # Fallback: detect by file signature
        return FileHandler._detect_by_signature(content)
    
    @staticmethod
    def _detect_by_signature(content: bytes) -> Optional[str]:
        """Detect file type by file signature (magic bytes)"""
        if len(content) < 4:
            return None
        
        # PDF signature
        if content.startswith(b'%PDF'):
            return 'application/pdf'
        
        # WAV signature
        if content.startswith(b'RIFF') and content[8:12] == b'WAVE':
            return 'audio/wav'
        
        # MP3 signature
        if content.startswith(b'ID3') or content.startswith(b'\xff\xfb'):
            return 'audio/mpeg'
        
        # DOCX/ZIP signature
        if content.startswith(b'PK\x03\x04'):
            # Could be DOCX or other ZIP-based format
            return 'application/zip'
        
        return None
    
    @staticmethod
    def validate_file_size(file_size: int, max_size_mb: Optional[int] = None) -> bool:
        """Validate file size against limits"""
        max_size = max_size_mb or settings.max_file_size_mb
        max_bytes = max_size * 1024 * 1024
        return file_size <= max_bytes
    
    @staticmethod
    def is_supported_document_type(content_type: str) -> bool:
        """Check if document type is supported"""
        return content_type in SUPPORTED_DOCUMENT_TYPES
    
    @staticmethod
    def is_supported_audio_type(content_type: str) -> bool:
        """Check if audio type is supported"""
        return content_type in SUPPORTED_AUDIO_TYPES
    
    @staticmethod
    def get_file_extension(filename: str) -> str:
        """Get file extension from filename"""
        return Path(filename).suffix.lower()
    
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """Sanitize filename for safe storage"""
        # Remove potentially dangerous characters
        import re
        sanitized = re.sub(r'[^\w\s\-_\.]', '', filename)
        
        # Limit length
        if len(sanitized) > 255:
            name, ext = os.path.splitext(sanitized)
            sanitized = name[:250] + ext
        
        return sanitized
    
    async def save_temp_file(self, file: UploadFile) -> str:
        """Save uploaded file to temporary location"""
        try:
            # Generate unique filename
            import uuid
            temp_filename = f"{uuid.uuid4()}_{self.sanitize_filename(file.filename)}"
            temp_path = os.path.join(self.temp_dir, temp_filename)
            
            # Save file
            content = await file.read()
            with open(temp_path, 'wb') as temp_file:
                temp_file.write(content)
            
            # Reset file pointer
            await file.seek(0)
            
            logger.info(f"Saved temporary file: {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"Error saving temporary file: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to save temporary file: {str(e)}"
            )
    
    @staticmethod
    def cleanup_temp_file(file_path: str):
        """Remove temporary file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.debug(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Could not cleanup temporary file {file_path}: {e}")
    
    @staticmethod
    def get_file_info(file_path: str) -> Dict[str, Any]:
        """Get information about a file"""
        try:
            stat = os.stat(file_path)
            return {
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'created': stat.st_ctime,
                'exists': True
            }
        except Exception:
            return {'exists': False}
    
    @staticmethod
    def estimate_processing_time(file_size: int, file_type: str) -> float:
        """Estimate processing time based on file characteristics"""
        # Base time in seconds
        base_time = 5.0
        
        # Size factor (1 second per MB)
        size_mb = file_size / (1024 * 1024)
        size_time = size_mb * 1.0
        
        # Type factor
        if file_type in SUPPORTED_DOCUMENT_TYPES.values():
            type_multiplier = {
                'pdf': 1.5,
                'txt': 0.5,
                'docx': 2.0
            }.get(file_type, 1.0)
        elif file_type in SUPPORTED_AUDIO_TYPES.values():
            type_multiplier = {
                'mp3': 2.0,
                'wav': 1.5,
                'm4a': 2.5
            }.get(file_type, 2.0)
        else:
            type_multiplier = 1.0
        
        return (base_time + size_time) * type_multiplier
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    @staticmethod
    def is_text_file(content: bytes, max_check_bytes: int = 8192) -> bool:
        """Check if file content appears to be text"""
        try:
            # Check a sample of the file
            sample = content[:max_check_bytes]
            sample.decode('utf-8')
            
            # Check for common binary signatures
            binary_signatures = [
                b'\x00\x00',  # NULL bytes (common in binary)
                b'\xff\xd8\xff',  # JPEG
                b'\x89PNG',  # PNG
                b'%PDF',  # PDF
                b'RIFF'  # WAV/AVI
            ]
            
            for sig in binary_signatures:
                if sig in sample[:100]:
                    return False
            
            return True
            
        except UnicodeDecodeError:
            return False


class FileValidator:
    """Comprehensive file validation utility"""
    
    @staticmethod
    async def validate_upload(file: UploadFile, file_type: str = 'auto') -> Dict[str, Any]:
        """Comprehensive file validation"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'info': {}
        }
        
        try:
            # Read file content
            content = await file.read()
            await file.seek(0)  # Reset file pointer
            
            # Basic validations
            if not file.filename:
                validation_result['errors'].append("No filename provided")
                validation_result['valid'] = False
            
            if len(content) == 0:
                validation_result['errors'].append("File is empty")
                validation_result['valid'] = False
            
            # File size validation
            if not FileHandler.validate_file_size(len(content)):
                validation_result['errors'].append(
                    f"File too large: {FileHandler.format_file_size(len(content))} "
                    f"(max: {settings.max_file_size_mb}MB)"
                )
                validation_result['valid'] = False
            
            # Detect and validate file type
            detected_type = FileHandler.detect_file_type(file.filename, content)
            
            if file_type == 'document':
                if not FileHandler.is_supported_document_type(file.content_type):
                    validation_result['errors'].append(
                        f"Unsupported document type: {file.content_type}"
                    )
                    validation_result['valid'] = False
                    
            elif file_type == 'audio':
                if not FileHandler.is_supported_audio_type(file.content_type):
                    validation_result['errors'].append(
                        f"Unsupported audio type: {file.content_type}"
                    )
                    validation_result['valid'] = False
            
            # Store file information
            validation_result['info'] = {
                'filename': file.filename,
                'size_bytes': len(content),
                'size_formatted': FileHandler.format_file_size(len(content)),
                'content_type': file.content_type,
                'detected_type': detected_type,
                'file_hash': FileHandler.generate_file_hash(content),
                'estimated_processing_time': FileHandler.estimate_processing_time(
                    len(content), 
                    SUPPORTED_DOCUMENT_TYPES.get(file.content_type, 'unknown')
                )
            }
            
            return validation_result
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Validation error: {str(e)}")
            return validation_result
