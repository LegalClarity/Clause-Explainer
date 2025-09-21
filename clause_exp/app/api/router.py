from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from typing import Optional
import logging
import time
from datetime import datetime
from ..models import DocumentCreate, DocumentUpdate, ClauseCreate, ClauseUpdate, DocumentAnalysisResponse, ClauseDetailsResponse, RAGQueryRequest, RAGQueryResponse, ErrorResponse, ProcessingStatusResponse
from ..services import (
    mongodb_service, qdrant_service, document_processor,
    clause_extractor, ai_service, embedding_service, rag_service
)
from ..config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post(
    "/documents/analyze",
    response_model=DocumentAnalysisResponse,
    summary="Complete Document Analysis",
    description="Upload and analyze a legal document to extract clauses, assess severity, and provide contextual explanations"
)
async def analyze_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Legal document file (PDF, DOCX, TXT)"),
    document_type: str = Form(..., description="Document type: rental_agreement, loan_contract, terms_of_service")
):
    """Complete document analysis pipeline"""
    start_time = time.time()
    document_id = None

    try:
        # Validate file type
        allowed_extensions = ['.pdf', '.docx', '.txt']
        file_extension = file.filename.lower().split('.')[-1] if file.filename else ''
        if f'.{file_extension}' not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: .{file_extension}. Allowed extensions: {allowed_extensions}"
            )

        # Generate document ID
        import uuid
        document_id = f"doc_{uuid.uuid4().hex[:16]}"

        logger.info(f"Starting analysis for document {document_id}, type: {document_type}")

        # Step 1: Save and extract text from document
        file_path = await document_processor.save_uploaded_file(file)
        extracted_text, extraction_metadata = await document_processor.extract_text(file_path)

        # Create document record
        document_data = DocumentCreate(
            document_id=document_id,
            title=document_processor.get_document_title(extracted_text, file.filename),
            document_type=document_type,
            file_path=file_path,
            extracted_text=extracted_text,
            total_clauses=0,  # Will be updated
            processing_status="processing",
            metadata={
                "file_size": extraction_metadata.get("text_length", 0),
                "file_type": file.content_type,
                "language": document_processor.detect_language(extracted_text),
                **extraction_metadata
            }
        )

        await mongodb_service.create_document(document_data)

        # Step 2: Extract clauses
        clauses = clause_extractor.extract_clauses(extracted_text, document_id)

        if not clauses:
            raise HTTPException(status_code=400, detail="No clauses could be extracted from the document")

        # Store clauses in database
        await mongodb_service.create_clauses_batch(clauses)

        # Update document with clause count
        update_data = DocumentUpdate(total_clauses=len(clauses))
        await mongodb_service.update_document(document_id, update_data)

        # Step 3: Analyze clauses with AI
        clause_analysis_data = []
        for clause in clauses:
            clause_analysis_data.append({
                "clause_id": clause.clause_id,
                "text": clause.clause_text,
                "type": clause.clause_type
            })

        analysis_results = await ai_service.analyze_clauses_batch(clause_analysis_data, document_type)

        # Update clauses with analysis results
        for result in analysis_results:
            clause_id = result["clause_id"]
            analysis = result["analysis"]

            # Get severity color
            from ..models.clause import SEVERITY_COLORS
            severity_color = SEVERITY_COLORS.get(analysis.get("severity_level", 3), "#EAB308")

            update_data = ClauseUpdate(
                severity_level=analysis.get("severity_level", 3),
                severity_color=severity_color,
                risk_factors=analysis.get("risk_factors", []),
                legal_implications=analysis.get("legal_implications", ""),
                plain_language_explanation=analysis.get("plain_language_explanation", ""),
                compliance_flags=analysis.get("compliance_flags", [])
            )

            await mongodb_service.update_clause(clause_id, update_data)

        # Step 4: Generate embeddings and store in Qdrant
        updated_clauses = await mongodb_service.get_clauses_by_document(document_id)

        for clause in updated_clauses:
            try:
                # Generate embedding payload
                embedding_payload = await embedding_service.generate_clause_embedding_payload(
                    clause_id=clause.clause_id,
                    clause_text=clause.clause_text,
                    document_id=clause.document_id,
                    clause_type=clause.clause_type,
                    severity_level=clause.severity_level,
                    document_type=document_type
                )

                # Store in Qdrant
                success = await qdrant_service.store_clause_embedding(
                    clause_id=clause.clause_id,
                    vector=embedding_payload["vector"],
                    payload=embedding_payload["payload"]
                )

                if success:
                    update_data = ClauseUpdate(qdrant_stored=True)
                    await mongodb_service.update_clause(clause.clause_id, update_data)

            except Exception as e:
                logger.warning(f"Failed to store embedding for clause {clause.clause_id}: {e}")

        # Step 5: Generate document summary
        document_summary = await ai_service.generate_document_summary(analysis_results, document_type)

        # Step 6: Prepare timeline response
        timeline_items = []
        total_clauses = len(updated_clauses)

        for clause in updated_clauses:
            # Calculate timeline position
            percentage = ((clause.sequence_number - 1) / total_clauses) * 100

            # Determine visual indicator
            if clause.severity_level >= 4:
                visual_indicator = "circle_ring_red"
            elif clause.severity_level >= 3:
                visual_indicator = "circle_ring_orange"
            else:
                visual_indicator = "circle_ring_green"

            timeline_item = {
                "clause_id": clause.clause_id,
                "sequence_number": clause.sequence_number,
                "clause_title": clause.clause_title,
                "clause_text": clause.clause_text,
                "clause_type": clause.clause_type,
                "severity_level": clause.severity_level,
                "severity_color": clause.severity_color,
                "plain_language_explanation": clause.plain_language_explanation,
                "risk_factors": clause.risk_factors,
                "legal_implications": clause.legal_implications,
                "compliance_flags": clause.compliance_flags,
                "related_clauses": clause.related_clauses,
                "timeline_position": {
                    "percentage": round(percentage, 1),
                    "visual_indicator": visual_indicator
                }
            }
            timeline_items.append(timeline_item)

        # Step 7: Generate navigation data
        critical_checkpoints = [
            clause["sequence_number"] for clause in timeline_items
            if clause["severity_level"] >= 4
        ][:5]  # Top 5 critical clauses

        recommended_flow = sorted(
            list(set([1, total_clauses // 4, total_clauses // 2, 3 * total_clauses // 4, total_clauses]))
        )

        timeline_navigation = {
            "total_steps": total_clauses,
            "critical_checkpoints": critical_checkpoints,
            "recommended_flow": recommended_flow
        }

        # Step 8: Prepare final response
        processing_time = round(time.time() - start_time, 1)

        response = DocumentAnalysisResponse(
            document_id=document_id,
            document_metadata={
                "title": document_data.title,
                "document_type": document_type,
                "total_clauses": total_clauses,
                "overall_risk_score": round(sum(c.severity_level for c in updated_clauses) / total_clauses, 1),
                "processing_time": f"{processing_time}s",
                "compliance_status": "compliant" if document_summary["compliance_score"] > 75 else "partially_compliant" if document_summary["compliance_score"] > 50 else "non_compliant"
            },
            clause_timeline=timeline_items,
            document_summary=document_summary,
            timeline_navigation=timeline_navigation
        )

        # Update document status to completed
        await mongodb_service.update_document(document_id, DocumentUpdate(processing_status="completed"))

        logger.info(f"Completed analysis for document {document_id} in {processing_time}s")
        return response

    except HTTPException:
        raise
    except Exception as e:
        error_msg = f"Document analysis failed: {str(e)}"
        logger.error(f"{error_msg} for document {document_id}")

        # Update document status if it was created
        if document_id:
            try:
                await mongodb_service.update_document(document_id, DocumentUpdate(processing_status="failed"))
            except:
                pass

        raise HTTPException(status_code=500, detail=error_msg)

@router.get(
    "/documents/{document_id}/status",
    response_model=ProcessingStatusResponse,
    summary="Get Document Processing Status"
)
async def get_document_status(document_id: str):
    """Get the processing status of a document"""
    try:
        document = await mongodb_service.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")

        return ProcessingStatusResponse(
            document_id=document_id,
            status=document.processing_status,
            message=f"Document is {document.processing_status}"
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get document status for {document_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve document status")

@router.get(
    "/documents/{document_id}/clauses/{clause_id}/details",
    response_model=ClauseDetailsResponse,
    summary="Get Clause Details"
)
async def get_clause_details(document_id: str, clause_id: str):
    """Get detailed information about a specific clause"""
    try:
        clause = await mongodb_service.get_clause(clause_id)
        if not clause or clause.document_id != document_id:
            raise HTTPException(status_code=404, detail="Clause not found")

        # Get related clauses
        related_clauses = []
        if clause.related_clauses:
            for related_id in clause.related_clauses[:3]:  # Limit to 3
                related_clause = await mongodb_service.get_clause(related_id)
                if related_clause:
                    related_clauses.append(related_clause)

        # Get contextual explanation using RAG
        contextual_explanation = await rag_service.get_contextual_explanation(
            clause_text=clause.clause_text,
            clause_type=clause.clause_type,
            document_type="",  # Could be retrieved from document
            clause_id=clause_id
        )

        return ClauseDetailsResponse(
            clause=clause,
            related_clauses=related_clauses,
            contextual_explanation=contextual_explanation.get("explanation")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get clause details for {clause_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve clause details")

@router.post(
    "/rag/query",
    response_model=RAGQueryResponse,
    summary="Query Legal Knowledge Base"
)
async def query_rag(request: RAGQueryRequest):
    """Query the legal knowledge base with custom questions"""
    try:
        result = await rag_service.query_legal_database(
            query=request.query,
            document_type=request.document_id,  # This could be enhanced
            clause_types=None,  # Could be added to request
            limit=request.context_limit
        )

        return RAGQueryResponse(**result)

    except Exception as e:
        logger.error(f"Failed to process RAG query: {e}")
        raise HTTPException(status_code=500, detail="Failed to process query")

@router.post("/admin/initialize-knowledge-base")
async def initialize_knowledge_base():
    """Initialize the legal knowledge base (admin endpoint)"""
    try:
        await rag_service.initialize_legal_knowledge_base()
        return {"message": "Legal knowledge base initialized successfully"}

    except Exception as e:
        logger.error(f"Failed to initialize knowledge base: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize knowledge base")

@router.get("/health/ai-service")
async def check_ai_service_health():
    """Check the health status of AI services"""
    try:
        health_status = await ai_service.health_check()
        return {
            "status": "healthy" if health_status["openai"]["available"] or health_status["gemini"]["available"] else "unhealthy",
            "services": health_status
        }

    except Exception as e:
        logger.error(f"Failed to check AI service health: {e}")
        return {
            "status": "error",
            "error": str(e),
            "services": {
                "openai": {"available": False, "error": "Health check failed"},
                "gemini": {"available": False, "error": "Health check failed"},
                "preferred_client": None
            }
        }