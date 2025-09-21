from sentence_transformers import SentenceTransformer
import numpy as np
from typing import List, Dict, Any, Optional
import logging
from ..config.settings import settings

logger = logging.getLogger(__name__)

class EmbeddingServiceError(Exception):
    """Custom exception for embedding service errors"""
    pass

class EmbeddingService:
    """Service for generating text embeddings using sentence transformers"""

    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        """Load the sentence transformer model"""
        try:
            model_name = settings.embedding_model
            self.model = SentenceTransformer(model_name)
            logger.info(f"Loaded embedding model: {model_name}")

            # Verify model dimensions
            test_embedding = self.model.encode("test")
            if len(test_embedding) != settings.embedding_dimension:
                logger.warning(f"Model dimension {len(test_embedding)} doesn't match config {settings.embedding_dimension}")

        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise EmbeddingServiceError(f"Model loading failed: {str(e)}")

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text"""
        try:
            if not text or not text.strip():
                raise EmbeddingServiceError("Empty text provided for embedding")

            # Clean and prepare text
            text = self._preprocess_text(text)

            # Generate embedding
            embedding = self.model.encode(text, convert_to_numpy=True)

            # Convert to list and ensure correct dimension
            embedding_list = embedding.tolist() if hasattr(embedding, 'tolist') else list(embedding)

            # Truncate or pad to expected dimension if necessary
            if len(embedding_list) > settings.embedding_dimension:
                embedding_list = embedding_list[:settings.embedding_dimension]
            elif len(embedding_list) < settings.embedding_dimension:
                # Pad with zeros if shorter (unlikely with sentence transformers)
                embedding_list.extend([0.0] * (settings.embedding_dimension - len(embedding_list)))

            return embedding_list

        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise EmbeddingServiceError(f"Embedding generation failed: {str(e)}")

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts in batch"""
        try:
            if not texts:
                return []

            # Preprocess all texts
            processed_texts = [self._preprocess_text(text) for text in texts if text and text.strip()]

            if not processed_texts:
                raise EmbeddingServiceError("No valid texts provided for batch embedding")

            # Generate embeddings in batch
            embeddings = self.model.encode(processed_texts, convert_to_numpy=True, batch_size=32)

            # Convert to list of lists
            if hasattr(embeddings, 'tolist'):
                embeddings_list = embeddings.tolist()
            else:
                embeddings_list = [list(emb) for emb in embeddings]

            # Ensure all embeddings have correct dimension
            processed_embeddings = []
            for embedding in embeddings_list:
                if len(embedding) > settings.embedding_dimension:
                    embedding = embedding[:settings.embedding_dimension]
                elif len(embedding) < settings.embedding_dimension:
                    embedding.extend([0.0] * (settings.embedding_dimension - len(embedding)))
                processed_embeddings.append(embedding)

            logger.info(f"Generated {len(processed_embeddings)} embeddings in batch")
            return processed_embeddings

        except Exception as e:
            logger.error(f"Failed to generate batch embeddings: {e}")
            raise EmbeddingServiceError(f"Batch embedding generation failed: {str(e)}")

    def _preprocess_text(self, text: str) -> str:
        """Preprocess text for embedding generation"""
        if not text:
            return ""

        # Clean the text
        text = text.strip()

        # Remove excessive whitespace
        import re
        text = re.sub(r'\s+', ' ', text)

        # Limit text length for embedding (sentence transformers work better with reasonable lengths)
        max_length = 512  # Characters, not tokens
        if len(text) > max_length:
            # Try to cut at sentence boundary
            sentences = re.split(r'[.!?]+', text)
            processed_text = ""
            for sentence in sentences:
                if len(processed_text + sentence) <= max_length:
                    processed_text += sentence + ". "
                else:
                    break
            text = processed_text.strip()
        else:
            text = text[:max_length]

        return text

    async def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        try:
            # Convert to numpy arrays
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)

            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)

            if norm1 == 0 or norm2 == 0:
                return 0.0

            similarity = dot_product / (norm1 * norm2)

            # Ensure similarity is between -1 and 1
            return max(-1.0, min(1.0, similarity))

        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0

    async def find_most_similar(
        self,
        query_embedding: List[float],
        candidate_embeddings: List[List[float]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Find most similar embeddings to query"""
        try:
            similarities = []

            for i, candidate_emb in enumerate(candidate_embeddings):
                similarity = await self.calculate_similarity(query_embedding, candidate_emb)
                similarities.append({
                    "index": i,
                    "similarity": similarity
                })

            # Sort by similarity (descending)
            similarities.sort(key=lambda x: x["similarity"], reverse=True)

            return similarities[:top_k]

        except Exception as e:
            logger.error(f"Failed to find similar embeddings: {e}")
            return []

    async def generate_clause_embedding_payload(
        self,
        clause_id: str,
        clause_text: str,
        document_id: str,
        clause_type: str,
        severity_level: int,
        document_type: str
    ) -> Dict[str, Any]:
        """Generate embedding and payload for clause storage in Qdrant"""
        try:
            embedding = await self.generate_embedding(clause_text)

            payload = {
                "clause_id": clause_id,
                "document_id": document_id,
                "clause_type": clause_type,
                "severity_level": severity_level,
                "document_type": document_type,
                "clause_text": clause_text[:1000],  # Truncate for storage
                "legal_implications": "",  # Will be filled by AI analysis
                "risk_factors": []  # Will be filled by AI analysis
            }

            return {
                "clause_id": clause_id,
                "vector": embedding,
                "payload": payload
            }

        except Exception as e:
            logger.error(f"Failed to generate clause embedding payload for {clause_id}: {e}")
            raise EmbeddingServiceError(f"Clause embedding payload generation failed: {str(e)}")

    async def generate_legal_knowledge_payload(
        self,
        knowledge_id: str,
        content: str,
        title: str,
        content_type: str = "case_law",
        jurisdiction: str = "india",
        categories: Optional[List[str]] = None,
        authority_level: str = "medium"
    ) -> Dict[str, Any]:
        """Generate embedding and payload for legal knowledge storage"""
        try:
            embedding = await self.generate_embedding(content)

            payload = {
                "content_type": content_type,
                "title": title,
                "content": content[:2000],  # Truncate for storage
                "jurisdiction": jurisdiction,
                "categories": categories or [],
                "authority_level": authority_level,
                "relevance_topics": self._extract_relevance_topics(content)
            }

            return {
                "knowledge_id": knowledge_id,
                "vector": embedding,
                "payload": payload
            }

        except Exception as e:
            logger.error(f"Failed to generate legal knowledge payload for {knowledge_id}: {e}")
            raise EmbeddingServiceError(f"Legal knowledge embedding payload generation failed: {str(e)}")

    def _extract_relevance_topics(self, content: str) -> List[str]:
        """Extract relevance topics from legal content"""
        # Simple keyword-based topic extraction
        topics = []
        content_lower = content.lower()

        topic_keywords = {
            "termination": ["termination", "end", "cancel", "breach"],
            "payment": ["payment", "fee", "rent", "compensation"],
            "liability": ["liability", "responsible", "damage", "loss"],
            "notice": ["notice", "notify", "communication"],
            "deposit": ["deposit", "security", "refund"],
            "maintenance": ["maintenance", "repair", "condition"],
            "jurisdiction": ["court", "jurisdiction", "arbitration"],
            "confidentiality": ["confidential", "secret", "privacy"]
        }

        for topic, keywords in topic_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                topics.append(topic)

        return topics[:5]  # Limit to top 5 topics

# Global embedding service instance
embedding_service = EmbeddingService()
