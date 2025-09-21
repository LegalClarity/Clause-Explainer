from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, Range
from qdrant_client.http.exceptions import UnexpectedResponse
from typing import List, Dict, Any, Optional
import logging
import hashlib
import uuid
from ..config.settings import settings

logger = logging.getLogger(__name__)

class QdrantService:
    """Service for managing vector operations with Qdrant"""

    def _convert_to_valid_id(self, clause_id: str) -> str:
        """Convert clause ID to valid Qdrant UUID format"""
        # If already a valid UUID, return as-is
        try:
            uuid.UUID(clause_id)
            return clause_id
        except ValueError:
            pass

        # If it's already in our mapping cache, return the mapped ID
        if clause_id in self.id_mapping:
            return self.id_mapping[clause_id]

        # Generate a deterministic UUID based on the clause_id
        # This ensures the same clause_id always maps to the same UUID
        hash_obj = hashlib.sha256(clause_id.encode('utf-8'))
        hash_bytes = hash_obj.digest()

        # Convert first 16 bytes to UUID format
        uuid_bytes = hash_bytes[:16]
        generated_uuid = str(uuid.UUID(bytes=uuid_bytes))

        # Cache the mapping
        self.id_mapping[clause_id] = generated_uuid

        logger.debug(f"Converted clause ID '{clause_id}' to UUID '{generated_uuid}'")
        return generated_uuid

    def _get_original_id(self, qdrant_id: str) -> str:
        """Get original clause ID from Qdrant UUID (reverse mapping)"""
        for original_id, mapped_id in self.id_mapping.items():
            if mapped_id == qdrant_id:
                return original_id

        # If not in cache, return the UUID as-is (it might be a direct UUID)
        return qdrant_id

    def __init__(self):
        self.id_mapping = {}  # Cache for ID mappings
        self.client = None
        self._connected = False

        # Collection names
        self.clause_collection = "clause_embeddings"
        self.knowledge_collection = "legal_knowledge"

    async def initialize(self):
        """Initialize Qdrant connection and collections"""
        await self._ensure_connection()

    async def _ensure_connection(self):
        """Ensure Qdrant connection is established"""
        if self.client is None:
            try:
                # Check if host contains protocol (for Qdrant Cloud)
                qdrant_host = settings.qdrant_host
                if qdrant_host.startswith(('http://', 'https://')):
                    # Use URL parameter for Qdrant Cloud
                    self.client = QdrantClient(
                        url=qdrant_host,
                        api_key=settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None,
                        timeout=60.0
                    )
                else:
                    # Use host and port for local Qdrant
                    self.client = QdrantClient(
                        host=qdrant_host,
                        port=settings.qdrant_port,
                        api_key=settings.qdrant_api_key.get_secret_value() if settings.qdrant_api_key else None,
                        timeout=60.0
                    )
                # Test connection
                self.client.get_collections()
                self._connected = True
                logger.info("Connected to Qdrant successfully")

                # Initialize collections
                self._ensure_collections_exist()

            except Exception as e:
                logger.warning(f"Failed to connect to Qdrant: {e}")
                self._connected = False
                raise

    def _check_connection(self):
        """Check if connection is available, raise error if not"""
        if not self._connected or self.client is None:
            raise Exception("Qdrant connection not available. Please check your Qdrant server.")

    def _ensure_collections_exist(self):
        """Create collections if they don't exist"""
        try:
            # Check and create clause embeddings collection
            try:
                self.client.get_collection(self.clause_collection)
            except Exception:
                self.client.create_collection(
                    collection_name=self.clause_collection,
                    vectors_config=VectorParams(
                        size=settings.embedding_dimension,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {self.clause_collection}")

            # Check and create legal knowledge collection
            try:
                self.client.get_collection(self.knowledge_collection)
            except Exception:
                self.client.create_collection(
                    collection_name=self.knowledge_collection,
                    vectors_config=VectorParams(
                        size=settings.embedding_dimension,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {self.knowledge_collection}")

        except Exception as e:
            logger.error(f"Failed to initialize Qdrant collections: {e}")
            raise

    async def store_clause_embedding(
        self,
        clause_id: str,
        vector: List[float],
        payload: Dict[str, Any]
    ) -> bool:
        """Store clause embedding in vector database"""
        try:
            await self._ensure_connection()
            self._check_connection()

            # Convert to valid Qdrant ID
            valid_id = self._convert_to_valid_id(clause_id)

            # Add original ID to payload for retrieval
            enriched_payload = payload.copy()
            enriched_payload['original_clause_id'] = clause_id

            point = PointStruct(
                id=valid_id,
                vector=vector,
                payload=enriched_payload
            )

            self.client.upsert(
                collection_name=self.clause_collection,
                points=[point]
            )

            logger.info(f"Stored clause embedding: {clause_id} (Qdrant ID: {valid_id})")
            return True

        except Exception as e:
            logger.error(f"Failed to store clause embedding {clause_id}: {e}")
            return False

    async def store_legal_knowledge(
        self,
        knowledge_id: str,
        vector: List[float],
        payload: Dict[str, Any]
    ) -> bool:
        """Store legal knowledge embedding"""
        try:
            await self._ensure_connection()
            self._check_connection()

            point = PointStruct(
                id=knowledge_id,
                vector=vector,
                payload=payload
            )

            self.client.upsert(
                collection_name=self.knowledge_collection,
                points=[point]
            )

            logger.info(f"Stored legal knowledge: {knowledge_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to store legal knowledge {knowledge_id}: {e}")
            return False

    async def search_similar_clauses(
        self,
        query_vector: List[float],
        document_type: Optional[str] = None,
        clause_type: Optional[str] = None,
        severity_level: Optional[int] = None,
        limit: int = 5,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar clauses using vector similarity"""
        try:
            await self._ensure_connection()
            self._check_connection()

            # Build filter conditions
            conditions = []

            if document_type:
                conditions.append(
                    FieldCondition(
                        key="document_type",
                        match=MatchValue(value=document_type)
                    )
                )

            if clause_type:
                conditions.append(
                    FieldCondition(
                        key="clause_type",
                        match=MatchValue(value=clause_type)
                    )
                )

            if severity_level is not None:
                conditions.append(
                    FieldCondition(
                        key="severity_level",
                        range=Range(gte=severity_level)
                    )
                )

            filter_obj = Filter(must=conditions) if conditions else None

            results = self.client.search(
                collection_name=self.clause_collection,
                query_vector=query_vector,
                query_filter=filter_obj,
                limit=limit,
                score_threshold=score_threshold
            )

            return [
                {
                    "id": hit.payload.get('original_clause_id', hit.id),  # Return original clause ID
                    "score": hit.score,
                    "payload": hit.payload
                }
                for hit in results
            ]

        except Exception as e:
            logger.error(f"Failed to search similar clauses: {e}")
            return []

    async def search_legal_knowledge(
        self,
        query_vector: List[float],
        categories: Optional[List[str]] = None,
        jurisdiction: Optional[str] = None,
        authority_level: Optional[str] = None,
        limit: int = 3,
        score_threshold: float = 0.6
    ) -> List[Dict[str, Any]]:
        """Search legal knowledge base"""
        try:
            await self._ensure_connection()
            self._check_connection()

            conditions = []

            if jurisdiction:
                conditions.append(
                    FieldCondition(
                        key="jurisdiction",
                        match=MatchValue(value=jurisdiction)
                    )
                )

            if authority_level:
                conditions.append(
                    FieldCondition(
                        key="authority_level",
                        match=MatchValue(value=authority_level)
                    )
                )

            if categories:
                # Match any of the categories
                category_conditions = []
                for category in categories:
                    category_conditions.append(
                        FieldCondition(
                            key="categories",
                            match=MatchValue(value=category)
                        )
                    )
                if category_conditions:
                    conditions.extend(category_conditions)

            filter_obj = Filter(should=category_conditions) if category_conditions else None

            results = self.client.search(
                collection_name=self.knowledge_collection,
                query_vector=query_vector,
                query_filter=filter_obj,
                limit=limit,
                score_threshold=score_threshold
            )

            return [
                {
                    "id": hit.id,
                    "score": hit.score,
                    "payload": hit.payload
                }
                for hit in results
            ]

        except Exception as e:
            logger.error(f"Failed to search legal knowledge: {e}")
            return []

    async def get_clause_vector(self, clause_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a clause vector and payload by ID"""
        try:
            await self._ensure_connection()
            self._check_connection()

            # Convert to valid Qdrant ID
            valid_id = self._convert_to_valid_id(clause_id)

            results = self.client.retrieve(
                collection_name=self.clause_collection,
                ids=[valid_id]
            )

            if results:
                point = results[0]
                # Return original clause ID in the response
                payload = point.payload.copy()
                original_id = payload.pop('original_clause_id', clause_id)

                return {
                    "id": original_id,  # Return original clause ID
                    "vector": point.vector,
                    "payload": payload
                }

            return None

        except Exception as e:
            logger.error(f"Failed to retrieve clause vector {clause_id}: {e}")
            return None

    async def find_related_clauses(
        self,
        clause_id: str,
        limit: int = 10,
        score_threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Find clauses related to a given clause"""
        try:
            await self._ensure_connection()
            self._check_connection()

            # Get the original clause vector
            original_clause = await self.get_clause_vector(clause_id)
            if not original_clause:
                return []

            # Convert to valid Qdrant ID for filtering
            valid_id = self._convert_to_valid_id(clause_id)

            # Search for similar clauses, excluding the original
            conditions = [
                FieldCondition(
                    key="id",
                    match=MatchValue(value=valid_id)
                )
            ]

            filter_obj = Filter(must_not=conditions)

            results = self.client.search(
                collection_name=self.clause_collection,
                query_vector=original_clause["vector"],
                query_filter=filter_obj,
                limit=limit,
                score_threshold=score_threshold
            )

            return [
                {
                    "id": hit.payload.get('original_clause_id', hit.id),  # Return original clause ID
                    "score": hit.score,
                    "payload": hit.payload
                }
                for hit in results
            ]

        except Exception as e:
            logger.error(f"Failed to find related clauses for {clause_id}: {e}")
            return []

    async def delete_clause_embedding(self, clause_id: str) -> bool:
        """Delete a clause embedding"""
        try:
            await self._ensure_connection()
            self._check_connection()

            # Convert to valid Qdrant ID
            valid_id = self._convert_to_valid_id(clause_id)

            self.client.delete(
                collection_name=self.clause_collection,
                points_selector={"ids": [valid_id]}
            )
            logger.info(f"Deleted clause embedding: {clause_id} (Qdrant ID: {valid_id})")
            return True

        except Exception as e:
            logger.error(f"Failed to delete clause embedding {clause_id}: {e}")
            return False

    async def batch_store_clauses(self, clause_data: List[Dict[str, Any]]) -> Dict[str, bool]:
        """Batch store multiple clause embeddings"""
        results = {}
        try:
            await self._ensure_connection()
            self._check_connection()

            points = []
            for data in clause_data:
                # Convert to valid Qdrant ID
                valid_id = self._convert_to_valid_id(data["clause_id"])

                # Add original ID to payload for retrieval
                enriched_payload = data["payload"].copy()
                enriched_payload['original_clause_id'] = data["clause_id"]

                points.append(PointStruct(
                    id=valid_id,
                    vector=data["vector"],
                    payload=enriched_payload
                ))

            self.client.upsert(
                collection_name=self.clause_collection,
                points=points
            )

            # Mark all as successful
            for data in clause_data:
                results[data["clause_id"]] = True
                valid_id = self._convert_to_valid_id(data["clause_id"])
                logger.info(f"Batch stored clause embedding: {data['clause_id']} (Qdrant ID: {valid_id})")

        except Exception as e:
            logger.error(f"Failed batch store clauses: {e}")
            # Mark all as failed
            for data in clause_data:
                results[data["clause_id"]] = False

        return results

    async def get_collection_stats(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """Get statistics for a collection"""
        try:
            await self._ensure_connection()
            self._check_connection()

            info = self.client.get_collection(collection_name)
            return {
                "vectors_count": info.vectors_count,
                "points_count": info.points_count,
                "status": info.status
            }
        except Exception as e:
            logger.error(f"Failed to get collection stats for {collection_name}: {e}")
            return None

# Global service instance
qdrant_service = QdrantService()
