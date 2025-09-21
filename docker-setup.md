# Docker Setup for Clause Explainer & Legal Summarizer APIs

This repository contains Dockerized versions of the Clause Explainer and Legal Summarizer APIs, providing a complete containerized solution for legal document processing and analysis.

## 🏗️ Architecture

The application consists of:
- **Main API**: Combined FastAPI application serving both services
- **MongoDB**: Document and metadata storage
- **Qdrant**: Vector database for semantic search
- **File Storage**: Persistent volumes for uploaded documents

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- At least 4GB RAM available
- Valid API keys for OpenAI and/or Google Cloud

### 1. Clone and Setup Environment

```bash
# Clone the repository
git clone <repository-url>
cd Clause-Explainer

# Copy environment template
cp .env.example .env

# Edit .env with your API keys and configuration
nano .env
```

### 2. Configure API Keys

Edit `.env` file and add your API keys:

```env
# Required: At least one AI provider
OPENAI_API_KEY=sk-your-openai-key
GOOGLE_API_KEY=your-google-api-key
GEMINI_API_KEY=your-gemini-key

# Google Cloud (if using Google services)
GOOGLE_PROJECT_ID=your-project-id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

### 3. Start Services

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f clause-explainer

# Check service health
docker-compose ps
```

### 4. Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# Check individual services
curl http://localhost:8000/clause_exp/health
curl http://localhost:8000/summariser/health
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | API server port | 8000 |
| `DEBUG` | Enable debug mode | false |
| `MONGODB_URL` | MongoDB connection string | mongodb://localhost:27017 |
| `QDRANT_HOST` | Qdrant server host | localhost |
| `OPENAI_API_KEY` | OpenAI API key | - |
| `GOOGLE_API_KEY` | Google API key | - |
| `MAX_FILE_SIZE_MB` | Maximum upload size | 100 |

See `.env.example` for complete configuration options.

### Google Cloud Setup

If using Google Cloud services:

1. Create a service account in Google Cloud Console
2. Download the JSON key file
3. Mount it in the container:

```yaml
services:
  clause-explainer:
    volumes:
      - ./path/to/service-account.json:/app/service-account.json
    environment:
      - GOOGLE_APPLICATION_CREDENTIALS=/app/service-account.json
```

## 🐳 Docker Commands

### Build and Run

```bash
# Build image only
docker build -t clause-explainer .

# Run single container (requires external MongoDB/Qdrant)
docker run -p 8000:8000 --env-file .env clause-explainer

# Full stack with Docker Compose
docker-compose up -d
```

### Development Mode

```bash
# Run with live code reload
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

# Access container shell
docker-compose exec clause-explainer bash

# View real-time logs
docker-compose logs -f
```

### Maintenance

```bash
# Stop services
docker-compose down

# Remove volumes (⚠️ deletes data)
docker-compose down -v

# Update images
docker-compose pull
docker-compose up -d

# Backup data
docker run --rm -v clause-explainer_mongodb_data:/data -v $(pwd):/backup alpine tar czf /backup/mongodb-backup.tar.gz /data
```

## 📊 Service Endpoints

### Health Checks
- `GET /health` - Combined service health
- `GET /clause_exp/health` - Clause explainer health
- `GET /summariser/health` - Summarizer health

### Clause Explainer API
- `POST /clause_exp/upload` - Upload document
- `GET /clause_exp/documents` - List documents
- `POST /clause_exp/explain` - Explain clauses
- `POST /clause_exp/timeline` - Generate timeline

### Legal Summarizer API
- `POST /summariser/documents/upload` - Upload document
- `POST /summariser/documents/summarize` - Summarize document
- `POST /summariser/audio/upload` - Upload audio
- `POST /summariser/audio/transcribe` - Transcribe audio

## 🔍 Monitoring and Troubleshooting

### Health Monitoring

```bash
# Check container status
docker-compose ps

# Monitor resource usage
docker stats

# Check service health endpoints
curl http://localhost:8000/health
```

### Logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs clause-explainer
docker-compose logs mongodb
docker-compose logs qdrant

# Follow logs in real-time
docker-compose logs -f clause-explainer
```

### Common Issues

1. **Port conflicts**: Change ports in `docker-compose.yml`
2. **Memory issues**: Increase Docker memory allocation
3. **API key errors**: Verify keys in `.env` file
4. **Database connection**: Check MongoDB/Qdrant container status

### Database Access

```bash
# MongoDB shell
docker-compose exec mongodb mongosh

# Qdrant web UI
open http://localhost:6333/dashboard

# Check Qdrant collections
curl http://localhost:6333/collections
```

## 📁 Data Persistence

Data is persisted in Docker volumes:
- `mongodb_data`: MongoDB database files
- `qdrant_data`: Qdrant vector database
- `./clause_exp/uploads`: Uploaded documents
- `./uploads`: Additional file storage

## 🔒 Security Considerations

- API keys are passed via environment variables
- Non-root user runs the application
- Health checks monitor service availability
- File uploads are size-limited
- CORS middleware configured for web access

## 🚀 Production Deployment

For production deployment:

1. Use a reverse proxy (nginx/traefik)
2. Enable SSL/TLS termination
3. Set up monitoring (Prometheus/Grafana)
4. Configure log aggregation
5. Use managed databases for better reliability
6. Set resource limits in docker-compose.yml

Example production compose snippet:

```yaml
services:
  clause-explainer:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
      restart_policy:
        condition: unless-stopped
```

## 📝 API Documentation

Once running, access interactive API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🤝 Contributing

1. Make changes to the codebase
2. Test with `docker-compose up --build`
3. Update documentation as needed
4. Submit pull request

## 📄 License

[Add your license information here]