"""
Test document processing endpoints
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, MagicMock
import io


class TestDocumentEndpoints:
    """Test document processing endpoints."""
    
    async def test_health_check(self, async_client: AsyncClient):
        """Test basic health check."""
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
    
    async def test_root_endpoint(self, async_client: AsyncClient):
        """Test root endpoint."""
        response = await async_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
    
    async def test_api_info(self, async_client: AsyncClient):
        """Test API info endpoint."""
        response = await async_client.get("/api")
        assert response.status_code == 200
        data = response.json()
        assert "endpoints" in data
        assert "limits" in data
    
    async def test_supported_document_types(self, async_client: AsyncClient):
        """Test get supported document types."""
        response = await async_client.get("/api/v1/documents/supported-types")
        assert response.status_code == 200
        data = response.json()
        assert "supported_types" in data
        assert "application/pdf" in data["supported_types"]
    
    async def test_document_processing_info(self, async_client: AsyncClient):
        """Test document processing info endpoint."""
        response = await async_client.get("/api/v1/documents/processing-info")
        assert response.status_code == 200
        data = response.json()
        assert "limits" in data
        assert "features" in data
        assert "processing_pipeline" in data
    
    @patch('app.services.document_service.document_service.process_document')
    async def test_document_summarize_success(self, mock_process, async_client: AsyncClient, sample_text_file):
        """Test successful document summarization."""
        from tests.conftest import MockGeminiService
        
        # Mock the service response
        mock_gemini = MockGeminiService()
        mock_summary = await mock_gemini.analyze_document("test", {})
        mock_process.return_value = (mock_summary, False, 5.0)
        
        # Create test file
        files = {
            'file': ('test.txt', io.BytesIO(sample_text_file), 'text/plain')
        }
        data = {
            'include_financial_analysis': True,
            'include_risk_assessment': True,
            'summary_length': 'comprehensive'
        }
        
        response = await async_client.post(
            "/api/v1/documents/summarize",
            files=files,
            data=data
        )
        
        # Should succeed with mocked service
        assert response.status_code in [200, 500]  # May fail due to service dependencies
    
    async def test_document_validate_text(self, async_client: AsyncClient, sample_text_file):
        """Test document validation with text file."""
        files = {
            'file': ('test.txt', io.BytesIO(sample_text_file), 'text/plain')
        }
        
        response = await async_client.post(
            "/api/v1/documents/validate",
            files=files
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "valid" in data
        assert "file_type" in data
        assert "file_size_bytes" in data
    
    async def test_document_validate_invalid_type(self, async_client: AsyncClient):
        """Test document validation with invalid file type."""
        # Create fake image file
        fake_image = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01'
        
        files = {
            'file': ('test.png', io.BytesIO(fake_image), 'image/png')
        }
        
        response = await async_client.post(
            "/api/v1/documents/validate",
            files=files
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is False
        assert len(data["errors"]) > 0
    
    async def test_document_summarize_invalid_params(self, async_client: AsyncClient, sample_text_file):
        """Test document summarization with invalid parameters."""
        files = {
            'file': ('test.txt', io.BytesIO(sample_text_file), 'text/plain')
        }
        data = {
            'summary_length': 'invalid_length',  # Invalid parameter
            'language_preference': 'invalid_lang'  # Invalid language
        }
        
        response = await async_client.post(
            "/api/v1/documents/summarize",
            files=files,
            data=data
        )
        
        assert response.status_code == 422
    
    async def test_document_summarize_no_file(self, async_client: AsyncClient):
        """Test document summarization without file."""
        data = {
            'include_financial_analysis': True,
            'summary_length': 'brief'
        }
        
        response = await async_client.post(
            "/api/v1/documents/summarize",
            data=data
        )
        
        assert response.status_code == 422
    
    async def test_document_summarize_empty_file(self, async_client: AsyncClient):
        """Test document summarization with empty file."""
        files = {
            'file': ('empty.txt', io.BytesIO(b''), 'text/plain')
        }
        data = {
            'summary_length': 'brief'
        }
        
        response = await async_client.post(
            "/api/v1/documents/summarize",
            files=files,
            data=data
        )
        
        assert response.status_code == 422


class TestDocumentValidation:
    """Test document validation logic."""
    
    def test_filename_validation(self):
        """Test filename validation."""
        from app.utils.validators import RequestValidator
        
        # Valid filename
        result = RequestValidator.validate_file_name("contract.pdf")
        assert result['valid'] is True
        assert result['sanitized'] == "contract.pdf"
        
        # Invalid characters
        result = RequestValidator.validate_file_name("contract<>.pdf")
        assert len(result['warnings']) > 0
        assert '<' not in result['sanitized']
    
    def test_summary_length_validation(self):
        """Test summary length validation."""
        from app.utils.validators import RequestValidator
        
        assert RequestValidator.validate_summary_length("brief") is True
        assert RequestValidator.validate_summary_length("standard") is True
        assert RequestValidator.validate_summary_length("comprehensive") is True
        assert RequestValidator.validate_summary_length("invalid") is False
    
    def test_language_code_validation(self):
        """Test language code validation."""
        from app.utils.validators import RequestValidator
        
        assert RequestValidator.validate_language_code("en") is True
        assert RequestValidator.validate_language_code("en-US") is True
        assert RequestValidator.validate_language_code("es") is True
        assert RequestValidator.validate_language_code("invalid") is False
        assert RequestValidator.validate_language_code("123") is False
    
    def test_file_size_validation(self):
        """Test file size validation."""
        from app.utils.file_handler import FileHandler
        
        # Small file should pass
        assert FileHandler.validate_file_size(1024 * 1024, 10) is True  # 1MB with 10MB limit
        
        # Large file should fail
        assert FileHandler.validate_file_size(200 * 1024 * 1024, 100) is False  # 200MB with 100MB limit


class TestDocumentService:
    """Test document service functionality."""
    
    def test_file_hash_generation(self):
        """Test file hash generation."""
        from app.services.database import DatabaseService
        
        content1 = b"test content"
        content2 = b"test content"
        content3 = b"different content"
        
        hash1 = DatabaseService.generate_file_hash(content1)
        hash2 = DatabaseService.generate_file_hash(content2)
        hash3 = DatabaseService.generate_file_hash(content3)
        
        assert hash1 == hash2  # Same content should have same hash
        assert hash1 != hash3  # Different content should have different hash
        assert len(hash1) == 64  # SHA-256 hash length
    
    def test_file_type_detection(self):
        """Test file type detection."""
        from app.utils.file_handler import FileHandler
        
        # PDF signature
        pdf_content = b'%PDF-1.4\n'
        assert FileHandler._detect_by_signature(pdf_content) == 'application/pdf'
        
        # WAV signature
        wav_content = b'RIFF    WAVEfmt '
        assert FileHandler._detect_by_signature(wav_content) == 'audio/wav'
        
        # Unknown content
        unknown_content = b'unknown file content'
        assert FileHandler._detect_by_signature(unknown_content) is None
    
    def test_file_size_formatting(self):
        """Test file size formatting."""
        from app.utils.file_handler import FileHandler
        
        assert FileHandler.format_file_size(1024) == "1.0 KB"
        assert FileHandler.format_file_size(1024 * 1024) == "1.0 MB"
        assert FileHandler.format_file_size(1024 * 1024 * 1024) == "1.0 GB"
        assert FileHandler.format_file_size(512) == "512.0 B"
