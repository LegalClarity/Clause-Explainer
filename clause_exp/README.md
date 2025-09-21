# Clause Explainer Timeline - FastAPI Backend

A comprehensive FastAPI backend service for analyzing legal documents, extracting clauses, and providing contextual explanations through Retrieval-Augmented Generation (RAG).

## Features

- **Document Processing**: Extract text from PDF, DOCX, and TXT legal documents
- **Clause Extraction**: Automatically identify and segment individual clauses
- **AI-Powered Analysis**: Analyze clauses for severity, risks, and legal implications using OpenAI GPT-4 or Google Gemini
- **Vector Search**: Store and retrieve clause embeddings using Qdrant vector database
- **RAG System**: Provide contextual explanations using similar cases and legal knowledge
- **Timeline Generation**: Create interactive timelines with severity indicators
- **MongoDB Storage**: Persist documents, clauses, and analysis metadata

## Technology Stack

- **Backend**: FastAPI (Python 3.9+)
- **Database**: MongoDB (with Motor async driver)
- **Vector Database**: Qdrant
- **AI Models**: OpenAI GPT-4 / Google Gemini
- **Embeddings**: Sentence Transformers
- **Document Processing**: PyPDF2, python-docx

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd clausex
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp env.example .env
   # Edit .env with your API keys and configuration
   ```

5. **Start MongoDB and Qdrant**
   ```bash
   # MongoDB (if using local instance)
   mongod

   # Qdrant (if using local instance)
   docker run -p 6333:6333 qdrant/qdrant
   ```

## Configuration

Create a `.env` file based on the provided `env.example` template:

```env
# Application Settings
DEBUG=false
APP_NAME="Clause Explainer Timeline API"
APP_VERSION="1.0.0"

# Server Settings
HOST=0.0.0.0
PORT=8000

# MongoDB Settings
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=clause_explainer

# Qdrant Settings
QDRANT_HOST=localhost
QDRANT_PORT=6333
# QDRANT_API_KEY=your-qdrant-api-key

# AI API Settings
OPENAI_API_KEY=your-openai-api-key
# GOOGLE_API_KEY=your-google-api-key
AI_MODEL_PREFERENCE=openai

# File Processing Settings
MAX_FILE_SIZE=52428800
```

## Running the Application

### Development Mode
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production Mode
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

## API Endpoints

### Main Analysis Endpoint
```
POST /api/v1/documents/analyze
```
Upload a legal document for complete analysis including clause extraction, AI analysis, and timeline generation.

**Request**: Multipart form data with file and document_type
**Response**: Complete analysis with timeline, severity scores, and recommendations

### Additional Endpoints
```
GET  /api/v1/documents/{document_id}/status          # Processing status
GET  /api/v1/documents/{document_id}/clauses/{clause_id}/details  # Clause details
POST /api/v1/rag/query                               # Query legal knowledge base
POST /api/v1/admin/initialize-knowledge-base         # Initialize legal knowledge (admin)
```

## API Response Structure

The main analysis endpoint returns:

```json
{
    "document_id": "doc_12345",
    "document_metadata": {
        "title": "Rental Agreement - Mumbai Property",
        "document_type": "rental_agreement",
        "total_clauses": 15,
        "overall_risk_score": 3.2,
        "processing_time": "45.3s",
        "compliance_status": "partially_compliant"
    },
    "clause_timeline": [
        {
            "clause_id": "clause_001",
            "sequence_number": 1,
            "clause_title": "Property Description",
            "clause_text": "The premises located at...",
            "clause_type": "property_details",
            "severity_level": 1,
            "severity_color": "#22C55E",
            "plain_language_explanation": "This clause simply describes the property...",
            "risk_factors": [],
            "legal_implications": "Standard property identification clause...",
            "compliance_flags": [],
            "timeline_position": {
                "percentage": 6.7,
                "visual_indicator": "circle_ring_green"
            }
        }
    ],
    "document_summary": {
        "high_risk_clauses": 3,
        "critical_issues": ["Insufficient termination notice"],
        "recommendations": ["Add 30-day notice period"],
        "compliance_score": 78.5
    },
    "timeline_navigation": {
        "total_steps": 15,
        "critical_checkpoints": [7, 12, 14],
        "recommended_flow": [1, 3, 7, 12, 14, 15]
    }
}
```

## Severity Analysis System

- **Level 1 (Green)**: Informational - Standard boilerplate
- **Level 2 (Light Green)**: Low Risk - Minor implications
- **Level 3 (Yellow)**: Moderate Risk - Requires attention
- **Level 4 (Orange)**: High Risk - Significant legal implications
- **Level 5 (Red)**: Critical Risk - Major financial/legal exposure

## Document Types Supported

- `rental_agreement`: Residential/commercial lease agreements
- `loan_contract`: Loan and financing agreements
- `terms_of_service`: Website/app terms and conditions
- Custom document types can be added

## Architecture

### Core Services

1. **Document Processing**: Text extraction from various file formats
2. **Clause Extraction**: NLP-based clause identification and segmentation
3. **AI Analysis**: Severity assessment and legal implication analysis
4. **Vector Operations**: Embedding generation and similarity search
5. **RAG System**: Contextual explanation generation
6. **Database Layer**: MongoDB for metadata, Qdrant for vectors

### Data Flow

1. **Upload** → Document saved and text extracted
2. **Extraction** → Clauses identified and segmented
3. **Analysis** → AI analysis for each clause
4. **Storage** → Clauses and embeddings stored in databases
5. **Timeline** → Generate interactive timeline with severity indicators
6. **Response** → Complete analysis returned to client

## Testing

Run the test suite:
```bash
pytest tests/
```

## Deployment

### Docker Deployment
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Setup
- MongoDB 4.4+
- Qdrant 1.0+
- Python 3.9+
- 4GB+ RAM recommended
- GPU optional (for faster embeddings)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Check the API documentation at `/docs`
- Review the logs for error details
- Ensure all environment variables are properly configured
