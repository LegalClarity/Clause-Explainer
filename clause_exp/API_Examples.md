# Clause Explainer API - Request/Response Examples

This document provides detailed examples of API requests and responses for the Clause Explainer Timeline API.

## 📄 Document Analysis

### POST /clause_exp/documents/analyze

**Request (multipart/form-data):**
```
Content-Type: multipart/form-data

file: legal_agreement.pdf
document_type: rental_agreement
```

**Successful Response (200):**
```json
{
  "document_id": "doc_a1b2c3d4e5f67890",
  "document_metadata": {
    "title": "Standard Residential Rental Agreement",
    "document_type": "rental_agreement",
    "total_clauses": 28,
    "overall_risk_score": 2.3,
    "processing_time": "42.7s",
    "compliance_status": "compliant"
  },
  "clause_timeline": [
    {
      "clause_id": "clause_001",
      "sequence_number": 1,
      "clause_title": "Parties to Agreement",
      "clause_text": "This Rental Agreement is made between Landlord and Tenant...",
      "clause_type": "identification",
      "severity_level": 1,
      "severity_color": "#10B981",
      "plain_language_explanation": "This section identifies who is renting the property and who owns it.",
      "risk_factors": [],
      "legal_implications": "Establishes the legal relationship between parties",
      "compliance_flags": ["standard"],
      "related_clauses": ["clause_005", "clause_012"],
      "timeline_position": {
        "percentage": 3.6,
        "visual_indicator": "circle_ring_green"
      }
    }
  ],
  "document_summary": {
    "high_risk_clauses": 2,
    "medium_risk_clauses": 8,
    "low_risk_clauses": 18,
    "critical_issues": [
      "Security deposit exceeds legal limit",
      "Pet policy may violate fair housing laws"
    ],
    "recommendations": [
      "Review security deposit amount against local laws",
      "Consult legal counsel regarding pet policy",
      "Consider adding dispute resolution clause"
    ],
    "compliance_score": 78.5,
    "overall_sentiment": "moderate_risk"
  },
  "timeline_navigation": {
    "total_steps": 28,
    "critical_checkpoints": [5, 12, 18, 25],
    "recommended_flow": [1, 7, 14, 21, 28]
  }
}
```

**Error Response (400 - Invalid File Type):**
```json
{
  "detail": "Unsupported file type: .exe. Allowed extensions: ['.pdf', '.docx', '.txt']"
}
```

## 📊 Document Status

### GET /api/v1/documents/{document_id}/status

**Request:**
```
GET /api/v1/documents/doc_a1b2c3d4e5f67890/status
```

**Response (200):**
```json
{
  "document_id": "doc_a1b2c3d4e5f67890",
  "status": "completed",
  "message": "Document is completed"
}
```

**Response (Processing - 200):**
```json
{
  "document_id": "doc_a1b2c3d4e5f67890",
  "status": "processing",
  "progress_percentage": 65.0,
  "estimated_time_remaining": "25s",
  "message": "Document is processing"
}
```

## 🔍 Clause Details

### GET /api/v1/documents/{document_id}/clauses/{clause_id}/details

**Request:**
```
GET /api/v1/documents/doc_a1b2c3d4e5f67890/clauses/clause_001/details
```

**Response (200):**
```json
{
  "clause": {
    "clause_id": "clause_001",
    "document_id": "doc_a1b2c3d4e5f67890",
    "sequence_number": 1,
    "clause_title": "Security Deposit Terms",
    "clause_text": "Tenant shall pay a security deposit of $2,500 upon execution of this agreement...",
    "clause_type": "financial",
    "severity_level": 4,
    "severity_color": "#EF4444",
    "plain_language_explanation": "You must pay $2,500 upfront as a deposit that may not be fully returned.",
    "risk_factors": [
      "Deposit exceeds 2 months rent (may violate state law)",
      "No clear conditions for deposit return",
      "Interest not guaranteed on deposit"
    ],
    "legal_implications": "Security deposits are regulated by state law. Excessive deposits may be illegal.",
    "compliance_flags": ["requires_review"],
    "related_clauses": ["clause_015", "clause_022"],
    "qdrant_stored": true,
    "metadata": {
      "word_count": 45,
      "complexity_score": 0.7
    }
  },
  "related_clauses": [
    {
      "clause_id": "clause_015",
      "clause_title": "Deposit Refund Policy",
      "clause_type": "financial",
      "severity_level": 3
    }
  ],
  "contextual_explanation": "Based on similar rental agreements, security deposits typically range from one to two months' rent. A $2,500 deposit for a property renting at $1,200/month exceeds standard limits in many jurisdictions. Consider negotiating this amount down or seeking legal advice to ensure compliance with local tenant protection laws."
}
```

## 🧠 RAG Query

### POST /api/v1/rag/query

**Request:**
```json
{
  "query": "What are the key financial risks in this rental agreement?",
  "document_id": "doc_a1b2c3d4e5f67890",
  "context_limit": 5
}
```

**Response (200):**
```json
{
  "query": "What are the key financial risks in this rental agreement?",
  "answer": "The rental agreement contains several financial risk factors: 1) Security deposit of $2,500 exceeds typical limits (may violate state law), 2) Late fees of $50/day are unusually high, 3) No provision for deposit interest, 4) Automatic rent increases without clear justification. These clauses should be reviewed by legal counsel.",
  "confidence_score": 0.89,
  "sources": [
    {
      "clause_id": "clause_008",
      "clause_text": "Security deposit requirements...",
      "relevance_score": 0.95
    },
    {
      "clause_id": "clause_012",
      "clause_text": "Late payment penalties...",
      "relevance_score": 0.87
    }
  ],
  "related_clauses": ["clause_008", "clause_012", "clause_020"]
}
```

## 🏥 Health Checks

### GET /health

**Response (200):**
```json
{
  "status": "healthy",
  "timestamp": 1695328800.123,
  "version": "1.0.0"
}
```

### GET /api/v1/health/ai-service

**Response (200):**
```json
{
  "status": "healthy",
  "services": {
    "openai": {
      "available": true,
      "model": "gpt-4",
      "response_time": "1.2s"
    },
    "gemini": {
      "available": true,
      "model": "gemini-pro",
      "response_time": "0.8s"
    },
    "preferred_client": "openai"
  }
}
```

## ⚙️ Admin Endpoints

### POST /api/v1/admin/initialize-knowledge-base

**Request:**
```
POST /api/v1/admin/initialize-knowledge-base
```

**Response (200):**
```json
{
  "message": "Legal knowledge base initialized successfully"
}
```

## 📋 Document Types

The API supports the following document types:

- `rental_agreement` - Residential rental contracts
- `loan_contract` - Loan and credit agreements
- `terms_of_service` - Website/app terms and conditions

## 🔍 Severity Levels

- **1**: Low Risk (Green) - Standard clauses, minimal legal risk
- **2**: Low-Moderate Risk (Light Green) - Minor concerns, generally acceptable
- **3**: Moderate Risk (Yellow) - Requires attention, potential issues
- **4**: High Risk (Orange) - Significant concerns, recommend legal review
- **5**: Critical Risk (Red) - Serious legal issues, high priority review needed

## 📊 Compliance Status

- `compliant` - Document meets legal standards
- `partially_compliant` - Some issues requiring attention
- `non_compliant` - Significant legal concerns

## ⏱️ Processing Times

Typical processing times:
- Small documents (< 10 pages): 15-30 seconds
- Medium documents (10-50 pages): 30-90 seconds
- Large documents (> 50 pages): 2-5 minutes

Use the status endpoint to monitor long-running processes.
