from typing import List, Dict, Any, Optional
import logging
from .embedding_service import embedding_service
from .qdrant_service import qdrant_service
from .ai_service import ai_service

logger = logging.getLogger(__name__)

class RAGServiceError(Exception):
    """Custom exception for RAG service errors"""
    pass

class RAGService:
    """Service for Retrieval-Augmented Generation using Qdrant and AI"""

    async def get_contextual_explanation(
        self,
        clause_text: str,
        clause_type: str,
        document_type: str,
        clause_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate contextual explanation for a clause using RAG"""
        try:
            # Generate embedding for the clause
            clause_embedding = await embedding_service.generate_embedding(clause_text)

            # Retrieve similar clauses from vector database
            similar_clauses = await qdrant_service.search_similar_clauses(
                query_vector=clause_embedding,
                document_type=document_type,
                clause_type=clause_type,
                limit=3,
                score_threshold=0.6
            )

            # Retrieve relevant legal knowledge
            legal_context = await qdrant_service.search_legal_knowledge(
                query_vector=clause_embedding,
                categories=[document_type, clause_type],
                jurisdiction="india",  # Focus on Indian law
                limit=2,
                score_threshold=0.5
            )

            # Find related clauses if clause_id provided
            related_clauses = []
            if clause_id:
                related = await qdrant_service.find_related_clauses(
                    clause_id=clause_id,
                    limit=3,
                    score_threshold=0.7
                )
                related_clauses = related

            # Combine context for AI explanation
            context = {
                "similar_clauses": similar_clauses,
                "legal_references": legal_context,
                "related_clauses": related_clauses,
                "clause_text": clause_text,
                "clause_type": clause_type,
                "document_type": document_type
            }

            # Generate AI-powered explanation
            explanation = await self._generate_ai_explanation(context)

            return {
                "explanation": explanation,
                "sources": {
                    "similar_clauses": len(similar_clauses),
                    "legal_references": len(legal_context),
                    "related_clauses": len(related_clauses)
                },
                "confidence_score": self._calculate_confidence_score(context),
                "context_used": bool(similar_clauses or legal_context or related_clauses)
            }

        except Exception as e:
            logger.error(f"Failed to generate contextual explanation: {e}")
            return {
                "explanation": "Unable to generate contextual explanation due to technical issues.",
                "sources": {"similar_clauses": 0, "legal_references": 0, "related_clauses": 0},
                "confidence_score": 0.1,
                "context_used": False
            }

    async def query_legal_database(
        self,
        query: str,
        document_type: Optional[str] = None,
        clause_types: Optional[List[str]] = None,
        limit: int = 5
    ) -> Dict[str, Any]:
        """Query the legal knowledge base with custom questions"""
        try:
            # Generate embedding for the query
            query_embedding = await embedding_service.generate_embedding(query)

            # Search legal knowledge
            legal_results = await qdrant_service.search_legal_knowledge(
                query_vector=query_embedding,
                categories=document_type if isinstance(document_type, list) else [document_type] if document_type else None,
                limit=limit,
                score_threshold=0.4
            )

            # Search relevant clauses if clause types specified
            clause_results = []
            if clause_types:
                for clause_type in clause_types:
                    clauses = await qdrant_service.search_similar_clauses(
                        query_vector=query_embedding,
                        clause_type=clause_type,
                        limit=2,
                        score_threshold=0.5
                    )
                    clause_results.extend(clauses)

            # Generate AI response based on retrieved context
            context = {
                "query": query,
                "legal_knowledge": legal_results,
                "relevant_clauses": clause_results[:5]  # Limit to top 5
            }

            ai_response = await self._generate_query_response(context)

            return {
                "query": query,
                "answer": ai_response,
                "sources": {
                    "legal_references": legal_results,
                    "relevant_clauses": clause_results[:5]
                },
                "confidence_score": self._calculate_query_confidence(context)
            }

        except Exception as e:
            logger.error(f"Failed to query legal database: {e}")
            return {
                "query": query,
                "answer": "Unable to process query due to technical issues. Please try again later.",
                "sources": {"legal_references": [], "relevant_clauses": []},
                "confidence_score": 0.0
            }

    async def _generate_ai_explanation(self, context: Dict[str, Any]) -> str:
        """Generate AI explanation using retrieved context"""
        try:
            similar_clauses = context.get("similar_clauses", [])
            legal_references = context.get("legal_references", [])
            related_clauses = context.get("related_clauses", [])

            # Build context string
            context_parts = []

            if similar_clauses:
                context_parts.append("Similar clauses from other documents:")
                for i, clause in enumerate(similar_clauses[:2], 1):
                    payload = clause.get("payload", {})
                    context_parts.append(f"{i}. {payload.get('clause_text', '')[:200]}...")

            if legal_references:
                context_parts.append("\nRelevant legal references:")
                for i, ref in enumerate(legal_references[:2], 1):
                    payload = ref.get("payload", {})
                    context_parts.append(f"{i}. {payload.get('title', '')}: {payload.get('content', '')[:200]}...")

            context_str = "\n".join(context_parts) if context_parts else "No specific context available."

            # Generate prompt for AI
            prompt = f"""
Based on the following legal context and the clause provided, generate a comprehensive explanation that includes:

1. Plain language summary
2. Key legal implications
3. Potential risks or concerns
4. Recommendations for the user

Legal Context:
{context_str}

Clause Type: {context.get('clause_type', 'Unknown')}
Document Type: {context.get('document_type', 'Unknown')}
Clause Text: {context.get('clause_text', '')}

Provide a detailed, helpful explanation that a non-lawyer can understand, while highlighting important legal considerations.
"""

            # Use AI service to generate explanation
            client = ai_service._get_preferred_client()

            if client == "openai":
                response = await ai_service._analyze_with_openai(prompt)
                return response.get("explanation", "AI explanation not available")
            else:
                response = await ai_service._analyze_with_gemini(prompt)
                return response.get("explanation", "AI explanation not available")

        except Exception as e:
            logger.error(f"Failed to generate AI explanation: {e}")
            return "Detailed explanation unavailable. Please consult with a legal professional for comprehensive analysis."

    async def _generate_query_response(self, context: Dict[str, Any]) -> str:
        """Generate AI response for custom queries"""
        try:
            query = context.get("query", "")
            legal_knowledge = context.get("legal_knowledge", [])
            relevant_clauses = context.get("relevant_clauses", [])

            # Build context string
            context_parts = []

            if legal_knowledge:
                context_parts.append("Relevant legal knowledge:")
                for i, knowledge in enumerate(legal_knowledge[:3], 1):
                    payload = knowledge.get("payload", {})
                    context_parts.append(f"{i}. {payload.get('title', '')}: {payload.get('content', '')[:300]}...")

            if relevant_clauses:
                context_parts.append("\nRelevant contract clauses:")
                for i, clause in enumerate(relevant_clauses[:3], 1):
                    payload = clause.get("payload", {})
                    context_parts.append(f"{i}. {payload.get('clause_text', '')[:200]}...")

            context_str = "\n".join(context_parts) if context_parts else "Limited legal context available."

            # Generate prompt
            prompt = f"""
Answer the following legal question based on the provided context. Be comprehensive but clear, and indicate when you're making general statements versus specific legal advice.

Question: {query}

Legal Context:
{context_str}

Important: This is general information, not formal legal advice. Users should consult qualified legal professionals for their specific situations.
"""

            # Get AI response
            client = ai_service._get_preferred_client()

            if client == "openai":
                response = await ai_service._analyze_with_openai(prompt)
                return response.get("answer", "Unable to generate response")
            else:
                response = await ai_service._analyze_with_gemini(prompt)
                return response.get("answer", "Unable to generate response")

        except Exception as e:
            logger.error(f"Failed to generate query response: {e}")
            return "Unable to process your query at this time. Please try rephrasing your question or consult a legal professional."

    def _calculate_confidence_score(self, context: Dict[str, Any]) -> float:
        """Calculate confidence score based on available context"""
        similar_clauses = len(context.get("similar_clauses", []))
        legal_refs = len(context.get("legal_references", []))
        related_clauses = len(context.get("related_clauses", []))

        # Base confidence
        confidence = 0.3

        # Add confidence based on context availability
        confidence += min(similar_clauses * 0.1, 0.3)  # Max 0.3 for similar clauses
        confidence += min(legal_refs * 0.2, 0.4)      # Max 0.4 for legal references
        confidence += min(related_clauses * 0.1, 0.2) # Max 0.2 for related clauses

        return min(confidence, 1.0)

    def _calculate_query_confidence(self, context: Dict[str, Any]) -> float:
        """Calculate confidence score for query responses"""
        legal_knowledge = len(context.get("legal_knowledge", []))
        relevant_clauses = len(context.get("relevant_clauses", []))

        confidence = 0.2  # Base confidence for queries

        # Add confidence based on available information
        confidence += min(legal_knowledge * 0.15, 0.4)
        confidence += min(relevant_clauses * 0.1, 0.3)

        return min(confidence, 1.0)

    async def initialize_legal_knowledge_base(self):
        """Initialize the legal knowledge base with common legal information"""
        try:
            # Sample legal knowledge for Indian context
            legal_knowledge = [
                {
                    "id": "rent_control_act_1",
                    "content": "Under the Maharashtra Rent Control Act, 1999, landlords must provide at least 30 days notice for termination of tenancy, except in cases of non-payment or breach of terms.",
                    "title": "Termination Notice Requirements - Maharashtra",
                    "content_type": "statute",
                    "jurisdiction": "india",
                    "categories": ["rental_agreement", "termination"],
                    "authority_level": "high"
                },
                {
                    "id": "security_deposit_1",
                    "content": "Security deposits cannot exceed 2 months rent for residential premises and 6 months for commercial premises under state rent control laws.",
                    "title": "Security Deposit Limits",
                    "content_type": "regulation",
                    "jurisdiction": "india",
                    "categories": ["rental_agreement", "security_deposit"],
                    "authority_level": "high"
                },
                {
                    "id": "model_tenancy_act_1",
                    "content": "The Model Tenancy Act, 2021 provides a standardized framework for rental agreements with mandatory clauses for maintenance, dispute resolution, and tenant rights.",
                    "title": "Model Tenancy Act Overview",
                    "content_type": "legislation",
                    "jurisdiction": "india",
                    "categories": ["rental_agreement", "compliance"],
                    "authority_level": "high"
                }
            ]

            # Store in Qdrant
            for knowledge in legal_knowledge:
                payload = await embedding_service.generate_legal_knowledge_payload(
                    knowledge_id=knowledge["id"],
                    content=knowledge["content"],
                    title=knowledge["title"],
                    content_type=knowledge["content_type"],
                    jurisdiction=knowledge["jurisdiction"],
                    categories=knowledge["categories"],
                    authority_level=knowledge["authority_level"]
                )

                success = await qdrant_service.store_legal_knowledge(
                    knowledge_id=knowledge["id"],
                    vector=payload["vector"],
                    payload=payload["payload"]
                )

                if success:
                    logger.info(f"Stored legal knowledge: {knowledge['id']}")
                else:
                    logger.warning(f"Failed to store legal knowledge: {knowledge['id']}")

        except Exception as e:
            logger.error(f"Failed to initialize legal knowledge base: {e}")

# Global RAG service instance
rag_service = RAGService()
