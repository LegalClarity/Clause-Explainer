"""
Text-to-Speech service for generating audio from text using Gemini TTS API
"""

import os
import tempfile
import math
import struct
from typing import Optional
from loguru import logger
from pydantic import SecretStr

from ..config import settings


class TTSService:
    """Service for converting text to speech using Gemini TTS API"""
    
    def __init__(self):
        self.client = None
        self.use_mock = False
        self.api_key = None  # Don't load from environment yet
        
    async def initialize(self):
        """Initialize the Text-to-Speech client and test connection"""
        try:
            from google.cloud import texttospeech
            logger.info("🔄 Initializing Google Cloud Text-to-Speech client...")

            # Check for API key from multiple sources
            api_key = None
            api_key_sources = ["GOOGLE_API_KEY", "GEMINI_API_KEY"]

            for env_var in api_key_sources:
                api_key_value = os.getenv(env_var, "")
                if api_key_value:
                    api_key = SecretStr(api_key_value)
                    self.api_key = api_key  # Store for later use
                    logger.info(f"✅ Found API key in {env_var}: ***{api_key_value[-4:]}")
                    break

            if not api_key or not api_key.get_secret_value():
                logger.error("❌ No API key found! TTS will FAIL without proper credentials.")
                logger.error("Please set one of these environment variables:")
                logger.error("1. GOOGLE_API_KEY - your Google Cloud API key")
                logger.error("2. GEMINI_API_KEY - your Gemini API key")
                logger.error("3. GOOGLE_CLOUD_PROJECT - your project ID")
                logger.error("See: https://cloud.google.com/text-to-speech/docs/quickstart")
                raise Exception("No API key found for Google Cloud TTS")

            # Set the API key for authentication
            os.environ["GOOGLE_API_KEY"] = api_key.get_secret_value()
            logger.info("✅ API key configured for Google Cloud TTS")

            self.client = texttospeech.TextToSpeechClient()
            logger.info("✅ TTS client initialized")

            # Test the TTS connection
            logger.info("🧪 Testing TTS API connection...")
            test_success = await self._test_tts_connection()
            if test_success:
                logger.info("✅ TTS API connection successful")
                logger.info("✅ Gemini TTS service initialized successfully")
                self.use_mock = False
            else:
                logger.error("❌ TTS API test failed - falling back to mock mode")
                logger.error("   This means TTS will create mock audio files")
                logger.error("   To fix: Check API key permissions and enable Text-to-Speech API")
                self.use_mock = True

        except ImportError as e:
            logger.error(f"❌ Google Cloud Text-to-Speech library not available: {e}")
            logger.error("   Install with: pip install google-cloud-texttospeech")
            logger.error("   Falling back to mock mode")
            self.use_mock = True
        except Exception as e:
            logger.error(f"❌ Failed to initialize TTS service: {e}")
            logger.error("   Falling back to mock mode")
            self.use_mock = True

    async def _test_tts_connection(self) -> bool:
        """Test TTS API connection with a simple request"""
        try:
            from google.cloud import texttospeech

            # Create a minimal test synthesis request
            synthesis_input = texttospeech.SynthesisInput(text="Test")
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name="en-US-Neural2-D"
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3
            )

            # Make a test request
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            if response.audio_content and len(response.audio_content) > 0:
                logger.info("🧪 TTS test successful - received audio content")
                return True
            else:
                logger.error("🧪 TTS test failed - no audio content received")
                return False

        except Exception as e:
            logger.error(f"🧪 TTS connection test failed: {e}")
            return False
    
    async def synthesize(
        self,
        prompt: str,
        text: str,
        model_name: str,
        output_filepath: str = "output.mp3",
        voice_name: str = "Charon",
        speaking_rate: float = 1.0,
        pitch: float = 0.0
    ) -> str:
        """
        Synthesizes speech from the input text and saves it to an MP3 file using Gemini TTS.

        Args:
            prompt: Stylisting instructions on how to synthesize the content in the text field.
            text: The text to synthesize.
            model_name: Gemini model to use (e.g., gemini-2.5-flash-preview-tts, gemini-2.5-pro-preview-tts)
            output_filepath: The path to save the generated audio file.
            voice_name: Name of the voice to use.
            speaking_rate: Speaking rate (0.25 to 4.0).
            pitch: Voice pitch (-20.0 to 20.0).

        Returns:
            Path to the generated audio file.
        """
        try:
            logger.info("=== TTS SYNTHESIS STARTED ===")
            logger.info(f"TTS Mode: {'MOCK' if self.use_mock else 'REAL'}")
            logger.info(f"Output file: {output_filepath}")
            logger.info(f"Model: {model_name}, Voice: {voice_name}")
            logger.info(f"Speaking rate: {speaking_rate}, Pitch: {pitch}")
            logger.info(f"Text length: {len(text)} characters")
            logger.info(f"Text preview: {text[:200]}...")

            # No mock mode - must use real TTS

            if not self.client:
                logger.error("TTS client not initialized")
                raise Exception("TTS client not initialized")

            try:
                from google.cloud import texttospeech
            except ImportError:
                logger.error("Google Cloud Text-to-Speech library not available")
                raise Exception("Missing google-cloud-texttospeech library")
            logger.info("Google Cloud TTS client initialized")

            logger.info("Creating synthesis input with prompt and text")
            synthesis_input = texttospeech.SynthesisInput(text=text, prompt=prompt)

            logger.info("Setting up voice parameters")
            # Select the voice you want to use
            voice = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name=voice_name,
                model_name=model_name
            )

            logger.info("Setting up audio configuration")
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.MP3,
                speaking_rate=speaking_rate,
                pitch=pitch
            )

            logger.info("Making TTS API request...")
            # Perform the text-to-speech request on the text input with the selected
            # voice parameters and audio file type
            response = self.client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            logger.info("TTS API request completed")

            # Check if we got audio content
            if not response.audio_content:
                logger.error("No audio content received from TTS API")
                raise Exception("No audio content received from TTS API")

            audio_size = len(response.audio_content)
            logger.info(f"Audio content received: {audio_size} bytes")

            # The response's audio_content is binary
            logger.info(f"Writing audio content to file: {output_filepath}")
            with open(output_filepath, "wb") as out:
                out.write(response.audio_content)

            # Verify file was created and has content
            if not os.path.exists(output_filepath):
                logger.error(f"Audio file was not created: {output_filepath}")
                raise Exception(f"Audio file was not created: {output_filepath}")

            file_size = os.path.getsize(output_filepath)
            logger.info(f"Audio file created successfully: {file_size} bytes")

            if file_size == 0:
                logger.error("Audio file is empty")
                raise Exception("Generated audio file is empty")

            logger.info("=== TTS SYNTHESIS COMPLETED SUCCESSFULLY ===")
            return output_filepath

        except Exception as e:
            logger.error("=== TTS SYNTHESIS FAILED ===")
            logger.error(f"Error synthesizing audio: {e}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    async def synthesize_document_summary(
        self,
        summary_text: str,
        document_title: str,
        output_filepath: Optional[str] = None,
        voice_name: str = "Charon",
        model_name: str = "gemini-2.5-pro-preview-tts",
        speaking_rate: float = 1.0,
        pitch: float = 0.0
    ) -> str:
        """
        Synthesize a document summary as speech.

        Args:
            summary_text: The summary text to convert to speech.
            document_title: Title of the document for context.
            output_filepath: Optional path to save the audio file.
            voice_name: Name of the voice to use.
            model_name: Gemini model to use.
            speaking_rate: Speaking rate adjustment.
            pitch: Voice pitch adjustment.

        Returns:
            Path to the generated audio file.
        """
        try:
            logger.info("=== DOCUMENT SUMMARY TTS STARTED ===")
            logger.info(f"Document title: {document_title}")
            logger.info(f"Summary text length: {len(summary_text)} characters")

            # Create a prompt that provides context for the TTS
            prompt = f"This is a summary of a legal document titled '{document_title}'. Read it clearly and professionally as a legal document summary."
            logger.info(f"TTS prompt: {prompt}")

            if not output_filepath:
                output_filepath = tempfile.mktemp(suffix='.mp3', prefix='legal_summary_')
                logger.info(f"Generated temp file path: {output_filepath}")

            logger.info("Calling main synthesize method...")
            result_path = await self.synthesize(
                prompt=prompt,
                text=summary_text,
                model_name=model_name,
                output_filepath=output_filepath,
                voice_name=voice_name,
                speaking_rate=speaking_rate,
                pitch=pitch
            )

            logger.info("=== DOCUMENT SUMMARY TTS COMPLETED ===")
            return result_path

        except Exception as e:
            logger.error("=== DOCUMENT SUMMARY TTS FAILED ===")
            logger.error(f"Error synthesizing document summary: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise


# Global TTS service instance
tts_service = TTSService()
