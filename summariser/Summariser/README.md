# Legal Document & Audio Summarizer - FastAPI Backend

A comprehensive FastAPI backend service that provides intelligent summarization of legal documents (PDFs, text files) and audio recordings (court hearings, depositions, legal consultations) using Google Cloud AI services.

## 🚀 Features

### Document Analysis
- **Supported Formats**: PDF, TXT, DOCX (up to 50 pages, 100MB)
- **Legal Risk Assessment**: Identify and categorize risks with severity levels
- **Financial Impact Analysis**: Assess potential costs and liabilities
- **Legal Framework Matching**: Cross-reference with relevant laws and regulations
- **Comprehensive Summaries**: Brief, standard, or comprehensive analysis levels

### Audio Processing
- **Supported Formats**: MP3, WAV, M4A (up to 3 hours, 100MB)
- **Speech-to-Text**: High-accuracy transcription with speaker diarization
- **Speaker Analysis**: Identify roles (judge, attorney, witness, etc.)
- **Action Item Extraction**: Automatically identify tasks and deadlines
- **Legal Citations**: Recognize legal references and case law

### AI-Powered Intelligence
- **Google Cloud Vertex AI**: Advanced analysis using Gemini models
- **Confidence Scoring**: Reliability metrics for all AI-generated content
- **Intelligent Caching**: Avoid reprocessing identical files
- **Multi-language Support**: Process documents in multiple languages

## 📋 Requirements

### System Requirements
- Python 3.9+
- MongoDB 4.4+
- Google Cloud Platform account
- 4GB+ RAM recommended
- 10GB+ storage space

### Google Cloud Services
- Vertex AI API (Gemini models)
- Speech-to-Text API
- Document AI API (optional)
- Cloud Storage (optional)

## 🛠️ Installation

### 1. Clone Repository
```bash
git clone <repository-url>
cd legal-summarizer
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Setup Google Cloud

#### Create Service Account
```bash
# Create service account
gcloud iam service-accounts create legal-summarizer-sa \
    --display-name="Legal Summarizer Service Account"

# Grant necessary permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:legal-summarizer-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:legal-summarizer-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/speech.admin"

# Create and download key
gcloud iam service-accounts keys create service-account.json \
    --iam-account=legal-summarizer-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com
```

#### Enable APIs
```bash
gcloud services enable aiplatform.googleapis.com
gcloud services enable speech.googleapis.com
gcloud services enable documentai.googleapis.com
```

### 4. Setup MongoDB

#### Local MongoDB
```bash
# Install MongoDB Community Edition
# https://docs.mongodb.com/manual/installation/

# Start MongoDB
mongod --dbpath /path/to/data/directory
```

#### MongoDB Atlas (Cloud)
1. Create account at [MongoDB Atlas](https://www.mongodb.com/atlas)
2. Create cluster and get connection string
3. Add IP address to whitelist

### 5. Environment Configuration
```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

#### Required Environment Variables
```env
# Google Cloud
GOOGLE_CLOUD_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
VERTEX_AI_REGION=us-central1

# MongoDB
MONGODB_CONNECTION_STRING=mongodb://localhost:27017
MONGODB_DATABASE_NAME=legal_summarizer

# Optional Configuration
DEBUG_MODE=true
LOG_LEVEL=INFO
MAX_FILE_SIZE_MB=100
ENABLE_CACHING=true
```

## 🐳 Docker Deployment

### Quick Start with Docker Compose
```bash
# Set required environment variables
export GOOGLE_CLOUD_PROJECT_ID=your-project-id

# Place service account key
mkdir credentials
cp /path/to/service-account.json credentials/

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api
```

### Manual Docker Build
```bash
# Build image
docker build -t legal-summarizer .

# Run with MongoDB
docker run -d --name mongodb mongo:7.0
docker run -d -p 8000:8000 \
    -e MONGODB_CONNECTION_STRING=mongodb://mongodb:27017 \
    -e GOOGLE_CLOUD_PROJECT_ID=your-project-id \
    -v $(pwd)/credentials:/app/credentials \
    --link mongodb \
    legal-summarizer
```

## 🚀 Usage

### Start Development Server
```bash
# Using uvicorn directly
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Using Python module
python -m app.main
```

### API Documentation
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

### Example API Calls

#### Document Summarization
```bash
curl -X POST "http://localhost:8000/api/v1/documents/summarize" \
     -F "file=@contract.pdf" \
     -F "include_financial_analysis=true" \
     -F "include_risk_assessment=true" \
     -F "summary_length=comprehensive"
```

#### Audio Summarization
```bash
curl -X POST "http://localhost:8000/api/v1/audio/summarize" \
     -F "file=@deposition.mp3" \
     -F "session_type=deposition" \
     -F "expected_language=en-US" \
     -F "include_speaker_analysis=true" \
     -F "include_action_items=true"
```

#### File Validation
```bash
# Validate document
curl -X POST "http://localhost:8000/api/v1/documents/validate" \
     -F "file=@document.pdf"

# Validate audio
curl -X POST "http://localhost:8000/api/v1/audio/validate" \
     -F "file=@audio.mp3"
```

## 📊 API Endpoints

### Documents
- `POST /api/v1/documents/summarize` - Summarize legal document
- `POST /api/v1/documents/validate` - Validate document file
- `GET /api/v1/documents/supported-types` - Get supported document types
- `GET /api/v1/documents/processing-info` - Get processing information

### Audio
- `POST /api/v1/audio/summarize` - Summarize legal audio
- `POST /api/v1/audio/validate` - Validate audio file
- `GET /api/v1/audio/supported-types` - Get supported audio types
- `GET /api/v1/audio/processing-info` - Get processing information
- `GET /api/v1/audio/session-types` - Get session type information

### Health & Monitoring
- `GET /health` - Basic health check
- `GET /health/detailed` - Detailed health information
- `GET /health/services` - Individual service status
- `GET /health/metrics` - Application metrics

## 🔧 Configuration

### File Size Limits
```env
MAX_FILE_SIZE_MB=100              # Maximum file size
MAX_DOCUMENT_PAGES=50             # Maximum PDF pages
MAX_AUDIO_DURATION_MINUTES=180    # Maximum audio duration
```

### Processing Configuration
```env
PROCESSING_TIMEOUT_SECONDS=1800   # Processing timeout
ENABLE_CACHING=true               # Enable result caching
CACHE_TTL_HOURS=24                # Cache time-to-live
```

### Logging Configuration
```env
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
DEBUG_MODE=false                  # Enable debug mode
```

## 🏗️ Architecture

### Project Structure
```
legal-summarizer/
├── app/
│   ├── main.py                   # FastAPI application
│   ├── config.py                 # Configuration settings
│   ├── models/                   # Pydantic models
│   │   ├── schemas.py            # Database schemas
│   │   └── requests.py           # Request/response models
│   ├── routers/                  # API route handlers
│   │   ├── documents.py          # Document endpoints
│   │   ├── audio.py              # Audio endpoints
│   │   └── health.py             # Health endpoints
│   ├── services/                 # Business logic
│   │   ├── database.py           # MongoDB operations
│   │   ├── document_service.py   # Document processing
│   │   ├── audio_service.py      # Audio processing
│   │   └── gemini_service.py     # AI analysis
│   └── utils/                    # Utility functions
│       ├── file_handler.py       # File operations
│       └── validators.py         # Input validation
├── tests/                        # Test files
├── requirements.txt              # Python dependencies
├── docker-compose.yml            # Docker configuration
├── Dockerfile                    # Docker image
└── README.md                     # This file
```

### Technology Stack
- **FastAPI**: Modern Python web framework
- **MongoDB**: Document database with Motor async driver
- **Google Cloud AI**: Vertex AI, Speech-to-Text, Document AI
- **Pydantic**: Data validation and serialization
- **Loguru**: Advanced logging
- **Docker**: Containerization

## 🧪 Testing

### Run Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio httpx

# Run all tests
pytest

# Run with coverage
pytest --cov=app tests/

# Run specific test file
pytest tests/test_documents.py -v
```

### Test Coverage Areas
- API endpoint testing
- Service integration testing
- File validation testing
- Error handling testing
- Performance testing

## 📈 Monitoring & Logging

### Application Logs
```bash
# View logs
tail -f logs/api.log

# Docker logs
docker-compose logs -f api
```

### Health Monitoring
```bash
# Basic health check
curl http://localhost:8000/health

# Detailed metrics
curl http://localhost:8000/health/detailed
```

### Performance Metrics
- Request processing time
- File processing duration
- AI service response time
- Database operation time
- Memory and CPU usage

## 🔒 Security Considerations

### Authentication
- Currently operates without authentication
- Implement OAuth2/JWT for production
- Add API key authentication
- Rate limiting recommended

### Data Protection
- Files processed in memory only
- Optional caching with MongoDB
- No permanent file storage
- Sensitive data handling protocols

### Network Security
- CORS configuration
- Trusted host middleware
- HTTPS recommended for production
- Input validation and sanitization

## 🚀 Production Deployment

### Performance Optimization
```bash
# Production server with multiple workers
uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000

# With Gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Load Balancing
- Use Nginx for load balancing
- Configure SSL/TLS certificates
- Set up health checks
- Implement rate limiting

### Scaling Considerations
- Horizontal scaling with multiple instances
- Database replication and sharding
- CDN for static content
- Auto-scaling based on load

## 🐛 Troubleshooting

### Common Issues

#### Google Cloud Authentication
```bash
# Verify credentials
export GOOGLE_APPLICATION_CREDENTIALS=./service-account.json
gcloud auth application-default print-access-token
```

#### MongoDB Connection
```bash
# Test connection
mongosh "mongodb://localhost:27017/legal_summarizer"

# Check logs
docker-compose logs mongodb
```

#### File Processing Errors
- Verify file format support
- Check file size limits
- Ensure sufficient memory
- Review processing logs

### Debug Mode
```env
DEBUG_MODE=true
LOG_LEVEL=DEBUG
```

## 📝 API Examples

### Python Client Example
```python
import requests
import json

# Document summarization
with open('contract.pdf', 'rb') as f:
    files = {'file': f}
    data = {
        'include_financial_analysis': True,
        'include_risk_assessment': True,
        'summary_length': 'comprehensive'
    }
    response = requests.post(
        'http://localhost:8000/api/v1/documents/summarize',
        files=files,
        data=data
    )
    result = response.json()
    print(json.dumps(result, indent=2))
```

### JavaScript Client Example
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('session_type', 'deposition');
formData.append('include_speaker_analysis', 'true');

fetch('http://localhost:8000/api/v1/audio/summarize', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For support and questions:
- Create an issue on GitHub
- Check the documentation
- Review the API examples
- Consult the troubleshooting guide

## 🔄 Version History

- **v1.0.0** - Initial release with full document and audio processing capabilities
- Comprehensive AI analysis with Google Cloud services
- MongoDB caching and performance optimization
- Docker deployment support
- Complete API documentation
