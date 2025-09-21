# Legal Document & Audio Summarizer API - Postman Collection

This Postman collection provides comprehensive testing coverage for the Legal Document & Audio Summarizer FastAPI service.

## 📋 Collection Overview

The collection includes the following endpoint categories:

### 🔍 Root Endpoints
- **Get API Information** (`GET /`) - Basic API information and capabilities
- **API Endpoints Info** (`GET /api`) - Detailed endpoint information and limits

### 📄 Document Processing
- **Summarize Legal Document** (`POST /api/v1/documents/summarize`) - Upload and analyze legal documents

### 🎵 Audio Processing
- **Convert PDF to Speech** (`POST /api/v1/audio/pdf-to-speech`) - Convert PDF documents to narrated audio

### 💊 Health & Monitoring
- **Basic Health Check** (`GET /health`) - Overall API and service health
- **Detailed Health Check** (`GET /health/detailed`) - System metrics and detailed status
- **Service Status** (`GET /health/services`) - Individual service availability
- **Application Metrics** (`GET /health/metrics`) - Monitoring metrics

## 🚀 Quick Start

### 1. Import the Collection

1. Open Postman
2. Click **Import** button
3. Select **File**
4. Choose `postman_collection.json`
5. Click **Import**

### 2. Import the Environment

1. In Postman, click **Import** again
2. Select **File**
3. Choose `postman_environment.json`
4. Click **Import**
5. Select the "Legal Summarizer API Environment" from the environment dropdown

### 3. Configure Environment Variables

Update the following environment variables in Postman:

```json
{
  "base_url": "http://localhost:8000",
  "test_document_path": "C:\\path\\to\\your\\test\\document.pdf"
}
```

## 📝 API Endpoints Details

### Document Summarization

**Endpoint:** `POST /api/v1/documents/summarize`

**Parameters:**
- `file`: Legal document (PDF, DOCX, TXT) - max 100MB
- `include_financial_analysis`: true/false
- `include_risk_assessment`: true/false
- `summary_length`: "brief", "standard", "comprehensive"
- `language_preference`: Language code (e.g., "en", "es")

**Response:** JSON with analysis results, risk assessment, and financial analysis.

### PDF-to-Speech Conversion

**Endpoint:** `POST /api/v1/audio/pdf-to-speech`

**Parameters:**
- `file`: PDF document only
- `document_title`: Title for the audio file
- `summary_length`: "brief", "standard", "comprehensive"
- `voice_name`: TTS voice (e.g., "Charon", "Kore", "Fenrir")
- `model_name`: Gemini TTS model
- `speaking_rate`: 0.25-4.0
- `pitch`: -20.0 to 20.0

**Response:** MP3 audio file download.

## 🔧 Configuration

### Supported File Types

**Documents:**
- PDF (up to 50 pages, 100MB)
- DOCX
- TXT

**Audio Output:**
- MP3 (from PDF-to-speech conversion)

### Processing Limits

- Max file size: 100MB
- Max document pages: 50
- Max audio duration: 180 minutes
- Processing timeout: 1800 seconds (30 minutes)

## 🧪 Testing Features

The collection includes:

### Automated Tests
- Response time validation (< 30 seconds for processing)
- Status code validation
- Header validation
- Request tracking with timestamps and IDs

### Test Scripts
```javascript
// Global test script runs on every request
pm.test('Response time is acceptable', function () {
    pm.expect(pm.response.responseTime).to.be.below(30000);
});

pm.test('Status code is valid', function () {
    pm.response.to.have.status(pm.response.code);
});
```

## 📊 Response Headers

Successful requests include:
- `X-Request-ID`: Unique request identifier
- `X-Process-Time`: Processing time in seconds
- `X-Confidence-Score`: AI confidence score (document endpoints)
- `X-File-Type`: File type information
- `X-Audio-Duration-Seconds`: Estimated audio duration (audio endpoints)

## 🔍 Error Handling

The API returns detailed error responses:
```json
{
  "error": "ValidationError",
  "message": "Request validation failed",
  "details": {
    "validation_errors": [...]
  },
  "timestamp": "2025-01-19T...",
  "request_id": "uuid..."
}
```

## 🌐 Environment Variables

### Required Variables
- `base_url`: API server URL
- `test_document_path`: Path to test document file

### Optional Variables
- `document_title`: Default document title
- `summary_length`: Default summary length
- `voice_name`: Default TTS voice
- `language_preference`: Default language

## 📈 Monitoring & Health Checks

Use the health endpoints to monitor:

1. **Basic Health** (`/health`) - Overall system status
2. **Detailed Health** (`/health/detailed`) - System metrics and database stats
3. **Service Status** (`/health/services`) - Individual service connectivity
4. **Metrics** (`/health/metrics`) - Performance metrics for alerting

## 🛠 Troubleshooting

### Common Issues

1. **File Upload Errors**
   - Ensure file path is correct in environment variables
   - Check file size limits (100MB max)
   - Verify supported file types

2. **Processing Timeouts**
   - Large documents may take time to process
   - Check `/health/detailed` for system load
   - Increase timeout in Postman settings

3. **Service Unavailable**
   - Check `/health` endpoint for service status
   - Verify Google Cloud credentials
   - Check database connectivity

### Debug Information

- Request IDs are logged for correlation
- Check application logs at `logs/api.log`
- Use detailed health checks for system diagnostics

## 📚 Additional Resources

- **API Documentation**: Visit `http://localhost:8000/docs` for interactive API docs
- **Alternative Docs**: `http://localhost:8000/redoc` for ReDoc documentation
- **Health Dashboard**: Use health endpoints for monitoring

## 🤝 Contributing

When adding new endpoints to the API:

1. Update the Postman collection with new requests
2. Add appropriate environment variables
3. Include test scripts for validation
4. Update this README with new endpoint documentation

## 📄 License

This Postman collection is part of the Legal Document & Audio Summarizer project.
