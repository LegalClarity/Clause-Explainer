"""
Validation utilities for the Legal Summarizer application
"""

import re
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from pydantic import ValidationError
from fastapi import HTTPException
from loguru import logger

from ..config import settings, LEGAL_FRAMEWORK_TYPES, RISK_SEVERITY_LEVELS, AUDIO_SESSION_TYPES, SPEAKER_ROLES


class RequestValidator:
    """Utility class for validating API requests"""
    
    @staticmethod
    def validate_summary_length(length: str) -> bool:
        """Validate summary length parameter"""
        valid_lengths = ['brief', 'standard', 'comprehensive']
        return length.lower() in valid_lengths
    
    @staticmethod
    def validate_language_code(language: str) -> bool:
        """Validate language code format"""
        # Basic validation for language codes (ISO 639-1 or RFC 5646)
        pattern = r'^[a-z]{2}(-[A-Z]{2})?$'
        return bool(re.match(pattern, language))
    
    @staticmethod
    def validate_session_type(session_type: str) -> bool:
        """Validate audio session type"""
        return session_type.lower() in AUDIO_SESSION_TYPES
    
    @staticmethod
    def validate_file_name(filename: str) -> Dict[str, Any]:
        """Validate and sanitize filename"""
        result = {
            'valid': True,
            'sanitized': filename,
            'warnings': []
        }
        
        if not filename:
            result['valid'] = False
            result['sanitized'] = f"unnamed_{uuid.uuid4().hex[:8]}"
            result['warnings'].append("No filename provided, generated one")
            return result
        
        # Check for dangerous characters
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\\', '/']
        if any(char in filename for char in dangerous_chars):
            # Sanitize filename
            sanitized = re.sub(r'[<>:"|?*\\/]', '_', filename)
            result['sanitized'] = sanitized
            result['warnings'].append("Filename contained dangerous characters, sanitized")
        
        # Check length
        if len(filename) > 255:
            base, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')
            truncated = base[:250 - len(ext) - 1]
            result['sanitized'] = f"{truncated}.{ext}" if ext else truncated
            result['warnings'].append("Filename too long, truncated")
        
        return result
    
    @staticmethod
    def validate_confidence_score(score: float) -> bool:
        """Validate confidence score range"""
        return 0.0 <= score <= 1.0
    
    @staticmethod
    def validate_timestamp(timestamp: float) -> bool:
        """Validate timestamp value"""
        return timestamp >= 0.0
    
    @staticmethod
    def validate_duration(duration: float) -> bool:
        """Validate duration value"""
        max_duration = settings.max_audio_duration_minutes * 60
        return 0.0 < duration <= max_duration


class ResponseValidator:
    """Utility class for validating API responses"""
    
    @staticmethod
    def validate_document_summary(summary_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate document summary data structure"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        required_fields = [
            'key_takeaways',
            'legal_risks', 
            'legal_frameworks',
            'financial_implications',
            'executive_summary',
            'confidence_score'
        ]
        
        # Check required fields
        for field in required_fields:
            if field not in summary_data:
                validation_result['errors'].append(f"Missing required field: {field}")
                validation_result['valid'] = False
        
        # Validate specific field types and values
        if 'confidence_score' in summary_data:
            if not RequestValidator.validate_confidence_score(summary_data['confidence_score']):
                validation_result['errors'].append("Invalid confidence score range")
                validation_result['valid'] = False
        
        # Validate legal risks
        if 'legal_risks' in summary_data:
            for i, risk in enumerate(summary_data['legal_risks']):
                if isinstance(risk, dict):
                    if 'severity' in risk and risk['severity'] not in RISK_SEVERITY_LEVELS:
                        validation_result['warnings'].append(
                            f"Risk {i}: Invalid severity level '{risk['severity']}'"
                        )
        
        # Validate legal frameworks
        if 'legal_frameworks' in summary_data:
            for i, framework in enumerate(summary_data['legal_frameworks']):
                if isinstance(framework, dict):
                    if 'framework_type' in framework and framework['framework_type'] not in LEGAL_FRAMEWORK_TYPES:
                        validation_result['warnings'].append(
                            f"Framework {i}: Invalid framework type '{framework['framework_type']}'"
                        )
        
        return validation_result
    
    @staticmethod
    def validate_audio_summary(summary_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate audio summary data structure"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        required_fields = [
            'session_overview',
            'key_participants',
            'major_topics',
            'decisions_made',
            'action_items',
            'executive_summary',
            'confidence_score'
        ]
        
        # Check required fields
        for field in required_fields:
            if field not in summary_data:
                validation_result['errors'].append(f"Missing required field: {field}")
                validation_result['valid'] = False
        
        # Validate confidence score
        if 'confidence_score' in summary_data:
            if not RequestValidator.validate_confidence_score(summary_data['confidence_score']):
                validation_result['errors'].append("Invalid confidence score range")
                validation_result['valid'] = False
        
        # Validate key participants
        if 'key_participants' in summary_data:
            for i, participant in enumerate(summary_data['key_participants']):
                if isinstance(participant, dict):
                    if 'role' in participant and participant['role'] not in SPEAKER_ROLES:
                        validation_result['warnings'].append(
                            f"Participant {i}: Invalid role '{participant['role']}'"
                        )
                    if 'estimated_speaking_time' in participant:
                        if not isinstance(participant['estimated_speaking_time'], (int, float)) or participant['estimated_speaking_time'] < 0:
                            validation_result['warnings'].append(
                                f"Participant {i}: Invalid speaking time"
                            )
        
        # Validate objections and rulings
        if 'objections_rulings' in summary_data:
            for i, ruling in enumerate(summary_data['objections_rulings']):
                if isinstance(ruling, dict):
                    if 'timestamp' in ruling:
                        if not RequestValidator.validate_timestamp(ruling['timestamp']):
                            validation_result['warnings'].append(
                                f"Ruling {i}: Invalid timestamp"
                            )
        
        return validation_result


class SecurityValidator:
    """Security-focused validation utilities"""
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 10000) -> str:
        """Sanitize text input to prevent injection attacks"""
        if not isinstance(text, str):
            return str(text)
        
        # Remove/escape potentially dangerous characters
        sanitized = text.replace('<', '&lt;').replace('>', '&gt;')
        
        # Limit length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length] + "..."
        
        return sanitized
    
    @staticmethod
    def validate_request_id(request_id: str) -> bool:
        """Validate request ID format"""
        # Should be a valid UUID format
        try:
            uuid.UUID(request_id)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def check_for_malicious_content(content: str) -> List[str]:
        """Check for potentially malicious content patterns"""
        warnings = []
        
        # Check for script tags
        if re.search(r'<script[^>]*>', content, re.IGNORECASE):
            warnings.append("Potential script injection detected")
        
        # Check for SQL injection patterns
        sql_patterns = [
            r"union\s+select",
            r"drop\s+table",
            r"insert\s+into",
            r"delete\s+from"
        ]
        
        for pattern in sql_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                warnings.append("Potential SQL injection pattern detected")
                break
        
        # Check for excessive repetition (potential DoS)
        if len(set(content.split())) < len(content.split()) * 0.1:
            warnings.append("Excessive repetition detected")
        
        return warnings


class BusinessLogicValidator:
    """Business logic validation utilities"""
    
    @staticmethod
    def validate_processing_limits(file_size: int, file_type: str) -> Dict[str, Any]:
        """Validate file against processing limits"""
        result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # File size limits
        max_size = settings.max_file_size_mb * 1024 * 1024
        if file_size > max_size:
            result['valid'] = False
            result['errors'].append(f"File size exceeds limit: {file_size} bytes (max: {max_size})")
        
        # Processing complexity estimates
        if file_type == 'pdf' and file_size > 50 * 1024 * 1024:  # 50MB
            result['warnings'].append("Large PDF may take significant time to process")
        
        if file_type in ['mp3', 'wav', 'm4a'] and file_size > 100 * 1024 * 1024:  # 100MB
            result['warnings'].append("Large audio file may take significant time to process")
        
        return result
    
    @staticmethod
    def validate_concurrent_requests(current_count: int) -> bool:
        """Validate if new request can be processed based on current load"""
        # This would integrate with actual load balancing
        max_concurrent = 50  # Example limit
        return current_count < max_concurrent
    
    @staticmethod
    def estimate_resource_usage(file_size: int, file_type: str) -> Dict[str, Any]:
        """Estimate resource usage for processing"""
        # Base memory usage in MB
        base_memory = 100
        
        # Additional memory per MB of file
        memory_per_mb = {
            'pdf': 2,
            'txt': 0.5,
            'docx': 3,
            'mp3': 1,
            'wav': 2,
            'm4a': 1.5
        }
        
        file_size_mb = file_size / (1024 * 1024)
        additional_memory = memory_per_mb.get(file_type, 1) * file_size_mb
        
        # Processing time estimate
        base_time = 5  # seconds
        time_per_mb = {
            'pdf': 2,
            'txt': 0.5,
            'docx': 3,
            'mp3': 10,  # Transcription is time-intensive
            'wav': 8,
            'm4a': 12
        }
        
        additional_time = time_per_mb.get(file_type, 2) * file_size_mb
        
        return {
            'estimated_memory_mb': base_memory + additional_memory,
            'estimated_time_seconds': base_time + additional_time,
            'complexity_score': min(10, (file_size_mb / 10) + (additional_time / 60))
        }


def create_validation_error(message: str, details: Optional[Dict[str, Any]] = None) -> HTTPException:
    """Create a standardized validation error response"""
    return HTTPException(
        status_code=422,
        detail={
            'error': 'ValidationError',
            'message': message,
            'details': details or {},
            'timestamp': datetime.utcnow().isoformat()
        }
    )


def log_validation_warning(message: str, context: Optional[Dict[str, Any]] = None):
    """Log validation warnings with context"""
    log_message = f"Validation warning: {message}"
    if context:
        log_message += f" | Context: {context}"
    logger.warning(log_message)
