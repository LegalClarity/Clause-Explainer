"""
Test configuration and fixtures
"""

import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from motor.motor_asyncio import AsyncIOMotorClient

from app.main import app
from app.config import settings
from app.services.database import db_service


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_client():
    """Create an async HTTP client for testing."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


@pytest.fixture(scope="session")
async def test_db():
    """Setup test database."""
    # Use test database
    test_db_name = f"{settings.mongodb_database_name}_test"
    
    # Connect to test database
    client = AsyncIOMotorClient(settings.mongodb_connection_string)
    database = client[test_db_name]
    
    yield database
    
    # Cleanup: drop test database
    await client.drop_database(test_db_name)
    client.close()


@pytest.fixture
async def sample_pdf_file():
    """Create a sample PDF file for testing."""
    import io
    from reportlab.pdfgen import canvas
    
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 750, "Sample Legal Document")
    p.drawString(100, 730, "This is a test contract for API testing.")
    p.drawString(100, 710, "Party A agrees to provide services to Party B.")
    p.drawString(100, 690, "Payment terms: Net 30 days.")
    p.showPage()
    p.save()
    
    buffer.seek(0)
    return buffer.getvalue()


@pytest.fixture
async def sample_text_file():
    """Create a sample text file for testing."""
    content = """
    LEGAL AGREEMENT

    This agreement is between Party A and Party B.
    
    Terms:
    1. Party A will provide consulting services
    2. Payment of $10,000 due within 30 days
    3. Confidentiality clause applies
    4. Termination clause: 30 days notice required
    
    Risk factors:
    - Late payment penalties may apply
    - Breach of confidentiality has legal consequences
    
    This document is legally binding.
    """
    return content.encode('utf-8')


@pytest.fixture
def sample_audio_data():
    """Create sample audio data for testing."""
    # This would be actual audio bytes in a real scenario
    # For testing, we'll use a placeholder
    return b"fake_audio_data_for_testing"


class MockGeminiService:
    """Mock Gemini service for testing."""
    
    async def analyze_document(self, text, options):
        from app.models.schemas import DocumentSummary, LegalRisk, LegalFramework, FinancialImplications
        
        return DocumentSummary(
            key_takeaways=["Test takeaway 1", "Test takeaway 2"],
            legal_risks=[
                LegalRisk(
                    risk_type="payment_risk",
                    severity="medium",
                    description="Late payment risk identified",
                    affected_clauses=["Payment terms"],
                    mitigation_suggestions=["Add penalty clause"]
                )
            ],
            legal_frameworks=[
                LegalFramework(
                    framework_type="contract_law",
                    name="Uniform Commercial Code",
                    relevance="Applies to commercial transactions",
                    citations=["UCC § 2-201"]
                )
            ],
            financial_implications=FinancialImplications(
                potential_costs="$10,000 contract value",
                liability_assessment="Limited liability",
                recommendations=["Review payment terms"]
            ),
            executive_summary="Test contract with standard terms",
            confidence_score=0.85
        )
    
    async def analyze_audio_transcription(self, transcription_data, options):
        from app.models.schemas import AudioSummary, KeyParticipant, ActionItem
        
        return AudioSummary(
            session_overview="Test deposition session",
            key_participants=[
                KeyParticipant(
                    speaker_id="speaker_1",
                    role="attorney",
                    estimated_speaking_time=120.0,
                    key_statements=["Test statement"]
                )
            ],
            major_topics=["Contract terms", "Payment dispute"],
            decisions_made=["Proceed with discovery"],
            action_items=[
                ActionItem(
                    description="Review contracts",
                    assigned_to="Legal team",
                    priority="high"
                )
            ],
            legal_citations=["Case v. Example, 123 F.3d 456"],
            objections_rulings=[],
            next_steps=["Schedule follow-up"],
            executive_summary="Productive deposition session",
            confidence_score=0.90,
            session_type="deposition"
        )
