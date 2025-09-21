# Clause Explainer Timeline API - Postman Collection

This Postman collection provides comprehensive API testing for the Clause Explainer Timeline API, a legal document analysis service that extracts clauses, assesses risk severity, and provides contextual explanations.

## 📋 Prerequisites

- Postman installed on your system
- Clause Explainer API running (default: http://localhost:8000)
- Sample legal documents for testing (PDF, DOCX, or TXT format)

## 🚀 Quick Start

1. **Import the Collection**
   - Open Postman
   - Click "Import" button
   - Select "File" tab
   - Choose `Clause_Explainer_Postman_Collection.json`
   - Click "Import"

2. **Configure Environment**
   - Create a new environment in Postman
   - Set the following variables:
     - `base_url`: `http://localhost:8000` (or your API URL)
     - `document_id`: Leave empty initially (will be set after document analysis)
     - `clause_id`: Leave empty initially (will be set after exploring clauses)

3. **Test Basic Connectivity**
   - Run the "API Root" request to verify the API is accessible
   - Run the "Health Check" request to ensure services are running

## 📚 API Endpoints Overview

### 🔍 Root Endpoints
- **GET /** - API information and available endpoints
- **GET /health** - Basic health check

### 📄 Document Analysis
- **POST /api/v1/documents/analyze** - Upload and analyze legal documents
- **GET /api/v1/documents/{document_id}/status** - Check processing status
- **GET /api/v1/documents/{document_id}/clauses/{clause_id}/details** - Get clause details

### 🧠 RAG Query System
- **POST /api/v1/rag/query** - Query legal knowledge base

### ⚙️ Admin & Maintenance
- **POST /api/v1/admin/initialize-knowledge-base** - Initialize knowledge base
- **GET /api/v1/health/ai-service** - Check AI service health

## 📝 Usage Examples

### 1. Document Analysis Workflow

1. **Analyze Document**
   ```
   POST /api/v1/documents/analyze
   Content-Type: multipart/form-data

   file: [your-legal-document.pdf]
   document_type: rental_agreement
   ```
   - Supported document types: `rental_agreement`, `loan_contract`, `terms_of_service`
   - Supported file formats: PDF, DOCX, TXT
   - Response includes: `document_id`, clause timeline, risk analysis, and navigation data

2. **Check Processing Status**
   ```
   GET /api/v1/documents/{document_id}/status
   ```
   - Monitor long-running document processing
   - Status values: `processing`, `completed`, `failed`

3. **Explore Clause Details**
   ```
   GET /api/v1/documents/{document_id}/clauses/{clause_id}/details
   ```
   - Get detailed analysis of specific clauses
   - Includes related clauses and contextual explanations

### 2. Query Legal Knowledge Base

```
POST /api/v1/rag/query
Content-Type: application/json

{
  "query": "What are the key risks in this rental agreement?",
  "document_id": "doc_1234567890abcdef",
  "context_limit": 5
}
```

### 3. Health Monitoring

- **AI Service Health**: Check OpenAI and Google Gemini API availability
- **General Health**: Basic API responsiveness check

## 🔧 Environment Variables

| Variable | Default Value | Description |
|----------|---------------|-------------|
| `base_url` | `http://localhost:8000` | API base URL |
| `document_id` | - | Document ID from analysis response |
| `clause_id` | - | Clause ID for detailed exploration |

## 📊 Response Formats

### Document Analysis Response
```json
{
  "document_id": "doc_1234567890abcdef",
  "document_metadata": {
    "title": "Rental Agreement Document",
    "document_type": "rental_agreement",
    "total_clauses": 25,
    "overall_risk_score": 2.8,
    "processing_time": "45.2s",
    "compliance_status": "partially_compliant"
  },
  "clause_timeline": [...],
  "document_summary": {...},
  "timeline_navigation": {...}
}
```

### Clause Details Response
```json
{
  "clause": {...},
  "related_clauses": [...],
  "contextual_explanation": "..."
}
```

### RAG Query Response
```json
{
  "query": "What are the key risks?",
  "answer": "...",
  "confidence_score": 0.85,
  "sources": [...],
  "related_clauses": [...]
}
```

## 🛠️ Troubleshooting

### Common Issues

1. **Connection Refused**
   - Ensure API is running on the specified port
   - Check firewall settings

2. **File Upload Issues**
   - Verify file format is supported (PDF, DOCX, TXT)
   - Check file size limits (default: 50MB)

3. **AI Service Unavailable**
   - Run "Check AI Service Health" endpoint
   - Verify API keys are configured

4. **Document Processing Timeout**
   - Large documents may take time to process
   - Use status endpoint to monitor progress

### Error Codes

- `400`: Bad Request (invalid file type, missing parameters)
- `404`: Not Found (document/clause doesn't exist)
- `500`: Internal Server Error (processing failed)

## 🔐 Authentication & Security

Currently, the API doesn't implement authentication. For production use, consider adding:

- API key authentication
- JWT tokens
- Rate limiting
- CORS configuration

## 📈 Testing Strategy

1. **Unit Testing**: Test individual endpoints
2. **Integration Testing**: Test complete workflows
3. **Load Testing**: Test with large documents
4. **Error Testing**: Test error scenarios

## 📞 Support

For API issues:
- Check the `/health` endpoint for service status
- Review application logs
- Verify configuration settings

## 🔄 Version History

- **v1.0.0**: Initial collection with core document analysis features
  - Document upload and analysis
  - Clause extraction and risk assessment
  - RAG query system
  - Health monitoring endpoints

---

**Note**: This collection is designed for the Clause Explainer Timeline API. Ensure your API instance is running and properly configured before testing.
