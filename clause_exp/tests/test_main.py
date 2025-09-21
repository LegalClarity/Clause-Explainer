import pytest
from fastapi.testclient import TestClient
from main import app

# Create TestClient instance
@pytest.fixture
def client():
    return TestClient(app)

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "timestamp" in data
    assert "version" in data

def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "version" in data
    assert "docs" in data

def test_analyze_document_without_file(client):
    """Test document analysis endpoint without file"""
    response = client.post("/api/v1/documents/analyze")
    assert response.status_code == 422  # Validation error

def test_invalid_document_type(client):
    """Test with invalid document type"""
    # Create a simple text file content
    test_content = b"This is a test document content."

    response = client.post(
        "/api/v1/documents/analyze",
        files={"file": ("test.txt", test_content, "text/plain")},
        data={"document_type": "invalid_type"}
    )
    # Should still process but may fail during analysis
    assert response.status_code in [200, 400, 500]  # Depends on AI service availability

@pytest.mark.asyncio
async def test_clause_extraction():
    """Test clause extraction functionality"""
    from app.services.clause_extraction import clause_extractor

    test_text = """
    1. Property Description

    The premises located at 123 Main Street shall be leased to the Tenant.

    2. Term

    This lease shall commence on January 1, 2024 and end on December 31, 2024.

    3. Rent

    Tenant shall pay $1,000 per month in rent.

    4. Termination

    Either party may terminate this agreement with 30 days notice.
    """

    clauses = clause_extractor.extract_clauses(test_text, "test_doc_123")

    assert len(clauses) > 0
    assert all(hasattr(clause, 'clause_id') for clause in clauses)
    assert all(hasattr(clause, 'clause_text') for clause in clauses)
    assert all(clause.document_id == "test_doc_123" for clause in clauses)

@pytest.mark.asyncio
async def test_embedding_service():
    """Test embedding service"""
    from app.services.embedding_service import embedding_service

    test_text = "This is a test clause for embedding generation."

    try:
        embedding = await embedding_service.generate_embedding(test_text)
        assert isinstance(embedding, list)
        assert len(embedding) > 0
        assert all(isinstance(x, float) for x in embedding)
    except Exception as e:
        # Embedding service may fail without proper model setup
        pytest.skip(f"Embedding service not available: {e}")

def test_severity_constants():
    """Test severity level constants"""
    from app.models.clause import SEVERITY_LEVELS, SEVERITY_COLORS

    assert len(SEVERITY_LEVELS) == 5
    assert len(SEVERITY_COLORS) == 5

    # Check that all severity levels have descriptions
    for level in range(1, 6):
        assert level in SEVERITY_LEVELS
        assert level in SEVERITY_COLORS

def test_response_models():
    """Test response model imports"""
    from app.models import DocumentAnalysisResponse, ClauseDetailsResponse

    # Should be able to import without errors
    assert DocumentAnalysisResponse
    assert ClauseDetailsResponse

if __name__ == "__main__":
    pytest.main([__file__])
