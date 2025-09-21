"""
Audio processing service for legal audio analysis
"""

import io
import time
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from fastapi import UploadFile, HTTPException
from google.cloud import speech
from loguru import logger
import wave
import struct

from ..config import settings, SUPPORTED_AUDIO_TYPES
from ..models.schemas import AudioSummary, AudioSummaryDocument, Transcription, SpeakerSegment
from ..models.requests import AudioSummarizeRequest
from ..services.database import db_service
from ..services.gemini_service import gemini_service
from ..utils.file_handler import FileHandler


class AudioService:
    """Service for processing legal audio recordings"""
    
    def __init__(self):
        self.speech_client = None
        self.file_handler = FileHandler()
        
    async def initialize(self):
        """Initialize the Speech-to-Text client"""
        try:
            self.speech_client = speech.SpeechClient()
            logger.info("Audio service initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize audio service: {e}")
            raise
    
    async def process_audio(self, file: UploadFile, request: AudioSummarizeRequest) -> Tuple[AudioSummary, Transcription, bool, float]:
        """
        Process a legal audio recording and return summary and transcription
        Returns: (summary, transcription, is_cached, processing_time)
        """
        start_time = time.time()
        
        try:
            # Read file content
            file_content = await file.read()
            file_hash = db_service.generate_file_hash(file_content)
            
            # Check for cached result
            cached_summary = await db_service.get_audio_summary_by_hash(file_hash)
            if cached_summary:
                processing_time = time.time() - start_time
                return cached_summary.summary, cached_summary.transcription, True, processing_time
            
            # Validate file
            audio_info = await self._validate_audio_file(file, file_content)
            
            # Convert audio to appropriate format for Speech-to-Text
            audio_data = await self._prepare_audio_for_transcription(file_content, file.content_type)
            
            # Transcribe audio with speaker diarization
            transcription = await self._transcribe_audio(audio_data, request)
            
            # Prepare options for Gemini analysis
            analysis_options = {
                'session_type': request.session_type,
                'include_speaker_analysis': request.include_speaker_analysis,
                'include_action_items': request.include_action_items,
                'summary_length': request.summary_length
            }
            
            # Analyze transcription with Gemini
            transcription_data = {
                'full_text': transcription.full_text,
                'speaker_segments': [seg.dict() for seg in transcription.speaker_segments],
                'language_code': transcription.language_code
            }
            
            summary = await gemini_service.analyze_audio_transcription(transcription_data, analysis_options)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            # Save to database if caching is enabled
            if settings.enable_caching:
                try:
                    summary_doc = AudioSummaryDocument(
                        audio_hash=file_hash,
                        filename=file.filename,
                        file_type=SUPPORTED_AUDIO_TYPES.get(file.content_type, 'unknown'),
                        file_size_bytes=len(file_content),
                        duration_seconds=audio_info['duration'],
                        processed_timestamp=datetime.utcnow(),
                        processing_time_seconds=processing_time,
                        session_type=request.session_type,
                        transcription=transcription,
                        summary=summary
                    )
                    await db_service.save_audio_summary(summary_doc)
                except Exception as e:
                    logger.warning(f"Failed to cache audio summary: {e}")
            
            logger.info(f"Audio processed successfully in {processing_time:.2f}s")
            return summary, transcription, False, processing_time
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to process audio: {str(e)}"
            )
    
    async def _validate_audio_file(self, file: UploadFile, file_content: bytes) -> Dict[str, Any]:
        """Validate uploaded audio file and return audio info"""
        # Check file type
        if file.content_type not in SUPPORTED_AUDIO_TYPES:
            supported_types = ", ".join(SUPPORTED_AUDIO_TYPES.keys())
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
        
        # Get audio duration (simplified - would need proper audio library)
        duration = await self._get_audio_duration(file_content, file.content_type)
        
        # Check duration limits
        max_duration = settings.max_audio_duration_minutes * 60
        if duration > max_duration:
            raise HTTPException(
                status_code=422,
                detail=f"Audio too long. Maximum duration: {settings.max_audio_duration_minutes} minutes"
            )
        
        audio_info = {
            'duration': duration,
            'file_size': len(file_content),
            'format': SUPPORTED_AUDIO_TYPES.get(file.content_type)
        }
        
        logger.info(f"Audio validation passed: {file.filename} ({duration:.1f}s, {len(file_content)} bytes)")
        return audio_info
    
    async def _get_audio_duration(self, file_content: bytes, content_type: str) -> float:
        """Get audio duration in seconds"""
        try:
            if content_type in ['audio/wav', 'audio/x-wav']:
                return await self._get_wav_duration(file_content)
            else:
                # For other formats, estimate based on file size and bitrate
                # This is a rough estimation - would need proper audio library
                estimated_bitrate = 128000  # 128 kbps average
                duration = (len(file_content) * 8) / estimated_bitrate
                return max(1.0, duration)  # Minimum 1 second
                
        except Exception as e:
            logger.warning(f"Could not determine audio duration: {e}")
            # Return estimated duration based on file size
            return max(1.0, len(file_content) / 32000)  # Rough estimate
    
    async def _get_wav_duration(self, file_content: bytes) -> float:
        """Get duration of WAV file"""
        try:
            file_like = io.BytesIO(file_content)
            with wave.open(file_like, 'rb') as wav_file:
                frames = wav_file.getnframes()
                sample_rate = wav_file.getframerate()
                duration = frames / float(sample_rate)
                return duration
        except Exception as e:
            logger.warning(f"Could not read WAV duration: {e}")
            return len(file_content) / 32000  # Fallback estimate
    
    async def _prepare_audio_for_transcription(self, file_content: bytes, content_type: str) -> bytes:
        """Prepare audio data for Google Speech-to-Text"""
        try:
            # For now, we'll pass the audio as-is
            # In production, you might want to convert to optimal format (LINEAR16, 16kHz)
            return file_content
            
        except Exception as e:
            logger.error(f"Error preparing audio: {e}")
            raise HTTPException(
                status_code=422,
                detail=f"Failed to prepare audio for transcription: {str(e)}"
            )
    
    async def _transcribe_audio(self, audio_data: bytes, request: AudioSummarizeRequest) -> Transcription:
        """Transcribe audio using Google Cloud Speech-to-Text"""
        try:
            # Determine audio encoding
            encoding = self._get_audio_encoding(request)
            
            # Configure recognition
            config = speech.RecognitionConfig(
                encoding=encoding,
                sample_rate_hertz=16000,  # Standard rate for legal audio
                language_code=request.expected_language,
                enable_automatic_punctuation=True,
                enable_speaker_diarization=request.enable_speaker_diarization,
                diarization_speaker_count_min=2,
                diarization_speaker_count_max=10,
                model="video",  # Good for legal proceedings
                use_enhanced=True,
                enable_word_time_offsets=True,
                enable_word_confidence=True
            )
            
            # Create audio object
            audio = speech.RecognitionAudio(content=audio_data)
            
            # Perform transcription
            def sync_transcribe():
                if len(audio_data) > 10 * 1024 * 1024:  # 10MB limit for sync
                    # Use long running recognize for large files
                    operation = self.speech_client.long_running_recognize(
                        config=config, audio=audio
                    )
                    return operation.result(timeout=settings.processing_timeout_seconds)
                else:
                    # Use synchronous recognize for smaller files
                    return self.speech_client.recognize(config=config, audio=audio)
            
            # Run in thread pool to avoid blocking
            response = await asyncio.get_event_loop().run_in_executor(None, sync_transcribe)
            
            # Process results
            full_text_parts = []
            speaker_segments = []
            total_confidence = 0.0
            confidence_count = 0
            
            for i, result in enumerate(response.results):
                alternative = result.alternatives[0]
                full_text_parts.append(alternative.transcript)
                
                # Calculate confidence
                confidence = alternative.confidence
                total_confidence += confidence
                confidence_count += 1
                
                # Extract speaker information if available
                if hasattr(result, 'speaker_tag') and result.speaker_tag:
                    speaker_id = f"speaker_{result.speaker_tag}"
                else:
                    speaker_id = f"speaker_unknown_{i}"
                
                # Get timing information
                start_time = 0.0
                end_time = 0.0
                if alternative.words:
                    start_time = alternative.words[0].start_time.total_seconds()
                    end_time = alternative.words[-1].end_time.total_seconds()
                
                speaker_segment = SpeakerSegment(
                    speaker_id=speaker_id,
                    text=alternative.transcript,
                    start_time=start_time,
                    end_time=end_time,
                    confidence=confidence
                )
                speaker_segments.append(speaker_segment)
            
            # Combine all text
            full_text = " ".join(full_text_parts)
            overall_confidence = total_confidence / max(confidence_count, 1)
            
            # Count words
            word_count = len(full_text.split())
            
            transcription = Transcription(
                full_text=full_text,
                speaker_segments=speaker_segments,
                language_code=request.expected_language,
                overall_confidence=overall_confidence,
                word_count=word_count
            )
            
            logger.info(f"Transcription completed: {word_count} words, {len(speaker_segments)} segments")
            return transcription
            
        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to transcribe audio: {str(e)}"
            )
    
    def _get_audio_encoding(self, request: AudioSummarizeRequest) -> speech.RecognitionConfig.AudioEncoding:
        """Determine audio encoding for Speech-to-Text"""
        # This would need to be determined based on the actual audio file
        # For now, we'll use a default encoding
        return speech.RecognitionConfig.AudioEncoding.LINEAR16
    
    async def validate_audio_file(self, file: UploadFile) -> Dict[str, Any]:
        """Validate audio file and return validation info"""
        try:
            file_content = await file.read()
            await file.seek(0)  # Reset file pointer
            
            validation_result = {
                'valid': True,
                'file_type': SUPPORTED_AUDIO_TYPES.get(file.content_type, 'unknown'),
                'file_size_bytes': len(file_content),
                'warnings': [],
                'errors': []
            }
            
            # File type validation
            if file.content_type not in SUPPORTED_AUDIO_TYPES:
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
            
            # Duration validation
            if validation_result['valid']:
                try:
                    duration = await self._get_audio_duration(file_content, file.content_type)
                    max_duration = settings.max_audio_duration_minutes * 60
                    
                    if duration > max_duration:
                        validation_result['valid'] = False
                        validation_result['errors'].append(f"Audio too long: {duration:.1f}s (max: {max_duration}s)")
                    
                    # Estimate processing time
                    estimated_time = self._estimate_processing_time(duration, len(file_content))
                    validation_result['estimated_processing_time'] = estimated_time
                    validation_result['duration_seconds'] = duration
                    
                except Exception as e:
                    validation_result['warnings'].append(f"Could not determine duration: {str(e)}")
            
            return validation_result
            
        except Exception as e:
            return {
                'valid': False,
                'file_type': 'unknown',
                'file_size_bytes': 0,
                'errors': [f"Validation error: {str(e)}"],
                'warnings': []
            }
    
    def _estimate_processing_time(self, duration: float, file_size: int) -> float:
        """Estimate processing time based on audio duration and file size"""
        # Base processing time
        base_time = 10.0
        
        # Transcription time (usually 0.3x to 0.5x of audio duration)
        transcription_time = duration * 0.4
        
        # Analysis time (additional 30 seconds for Gemini analysis)
        analysis_time = 30.0
        
        # Size factor (large files take longer to upload/process)
        size_mb = file_size / (1024 * 1024)
        size_factor = max(1.0, size_mb / 10)  # Increase time for files > 10MB
        
        return (base_time + transcription_time + analysis_time) * size_factor


# Global audio service instance
audio_service = AudioService()
