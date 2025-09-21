from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from pymongo.errors import ConnectionFailure, OperationFailure
from typing import List, Dict, Any, Optional
import logging
from ..config.settings import settings
from ..models import Document, DocumentCreate, DocumentUpdate, Clause, ClauseCreate, ClauseUpdate

logger = logging.getLogger(__name__)

class MongoDBService:
    """Service for MongoDB operations"""

    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self.documents_collection: Optional[AsyncIOMotorCollection] = None
        self.clauses_collection: Optional[AsyncIOMotorCollection] = None

    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(settings.mongodb_url)
            self.database = self.client[settings.mongodb_database]

            # Test connection
            await self.client.admin.command('ping')

            # Initialize collections
            self.documents_collection = self.database.documents
            self.clauses_collection = self.database.clauses

            # Create indexes
            await self._create_indexes()

            logger.info("Connected to MongoDB successfully")

        except ConnectionFailure as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def disconnect(self):
        """Disconnect from MongoDB"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    async def _create_indexes(self):
        """Create database indexes for optimal performance"""
        try:
            # Documents collection indexes
            await self.documents_collection.create_index("document_id", unique=True)
            await self.documents_collection.create_index("document_type")
            await self.documents_collection.create_index("processing_status")
            await self.documents_collection.create_index("upload_timestamp")
            await self.documents_collection.create_index("user_id")  # For user-specific queries

            # Clauses collection indexes
            await self.clauses_collection.create_index("clause_id", unique=True)
            await self.clauses_collection.create_index("document_id")
            await self.clauses_collection.create_index("clause_type")
            await self.clauses_collection.create_index("severity_level")
            await self.clauses_collection.create_index("sequence_number")
            await self.clauses_collection.create_index([("document_id", 1), ("sequence_number", 1)])
            await self.clauses_collection.create_index("user_id")  # For user-specific queries

            logger.info("Database indexes created successfully")

        except OperationFailure as e:
            logger.warning(f"Index creation failed (may already exist): {e}")

    # Document operations
    async def create_document(self, document_data: DocumentCreate) -> str:
        """Create a new document"""
        try:
            doc_dict = document_data.dict()
            result = await self.documents_collection.insert_one(doc_dict)
            logger.info(f"Created document: {document_data.document_id}")
            return str(result.inserted_id)

        except Exception as e:
            logger.error(f"Failed to create document {document_data.document_id}: {e}")
            raise

    async def get_documents_by_user(self, user_id: str, limit: int = 100) -> List[Document]:
        """Get documents for a specific user"""
        try:
            cursor = self.documents_collection.find(
                {"user_id": user_id}
            ).sort("upload_timestamp", -1).limit(limit)

            documents = []
            async for doc in cursor:
                documents.append(Document(**doc))

            return documents

        except Exception as e:
            logger.error(f"Failed to get documents for user {user_id}: {e}")
            raise

    async def get_document(self, document_id: str, user_id: Optional[str] = None) -> Optional[Document]:
        """Get document by ID"""
        try:
            filter_dict = {"document_id": document_id}
            if user_id:
                filter_dict["user_id"] = user_id

            doc = await self.documents_collection.find_one(filter_dict)
            if doc:
                return Document(**doc)
            return None

        except Exception as e:
            logger.error(f"Failed to get document {document_id}: {e}")
            raise

    async def update_document(self, document_id: str, update_data: DocumentUpdate) -> bool:
        """Update document"""
        try:
            update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
            if not update_dict:
                return False

            result = await self.documents_collection.update_one(
                {"document_id": document_id},
                {"$set": update_dict}
            )

            success = result.modified_count > 0
            if success:
                logger.info(f"Updated document: {document_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to update document {document_id}: {e}")
            raise

    async def delete_document(self, document_id: str, user_id: Optional[str] = None) -> bool:
        """Delete document and all its clauses"""
        try:
            # Build filter to optionally include user_id
            doc_filter = {"document_id": document_id}
            clause_filter = {"document_id": document_id}

            if user_id:
                doc_filter["user_id"] = user_id
                clause_filter["user_id"] = user_id

            # Delete document
            doc_result = await self.documents_collection.delete_one(doc_filter)

            # Delete all clauses for this document (and optionally user)
            clause_result = await self.clauses_collection.delete_many(clause_filter)

            success = doc_result.deleted_count > 0
            if success:
                logger.info(f"Deleted document {document_id} and {clause_result.deleted_count} clauses")

            return success

        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            raise

    async def get_documents_by_status(self, status: str, limit: int = 100) -> List[Document]:
        """Get documents by processing status"""
        try:
            cursor = self.documents_collection.find(
                {"processing_status": status}
            ).sort("upload_timestamp", -1).limit(limit)

            documents = []
            async for doc in cursor:
                documents.append(Document(**doc))

            return documents

        except Exception as e:
            logger.error(f"Failed to get documents by status {status}: {e}")
            raise

    # Clause operations
    async def create_clause(self, clause_data: ClauseCreate) -> str:
        """Create a new clause"""
        try:
            clause_dict = clause_data.dict()
            result = await self.clauses_collection.insert_one(clause_dict)
            logger.info(f"Created clause: {clause_data.clause_id}")
            return str(result.inserted_id)

        except Exception as e:
            logger.error(f"Failed to create clause {clause_data.clause_id}: {e}")
            raise

    async def create_clauses_batch(self, clauses_data: List[ClauseCreate]) -> List[str]:
        """Create multiple clauses in batch"""
        try:
            clauses_dict = [clause.dict() for clause in clauses_data]
            result = await self.clauses_collection.insert_many(clauses_dict)

            inserted_ids = [str(id) for id in result.inserted_ids]
            logger.info(f"Created {len(inserted_ids)} clauses in batch")
            return inserted_ids

        except Exception as e:
            logger.error(f"Failed to create clauses batch: {e}")
            raise

    async def get_clause(self, clause_id: str, user_id: Optional[str] = None) -> Optional[Clause]:
        """Get clause by ID"""
        try:
            filter_dict = {"clause_id": clause_id}
            if user_id:
                filter_dict["user_id"] = user_id

            clause = await self.clauses_collection.find_one(filter_dict)
            if clause:
                return Clause.from_mongo(clause)
            return None

        except Exception as e:
            logger.error(f"Failed to get clause {clause_id}: {e}")
            raise

    async def get_clauses_by_document(self, document_id: str, user_id: Optional[str] = None) -> List[Clause]:
        """Get all clauses for a document"""
        try:
            filter_dict = {"document_id": document_id}
            if user_id:
                filter_dict["user_id"] = user_id

            cursor = self.clauses_collection.find(filter_dict).sort("sequence_number", 1)

            clauses = []
            async for clause in cursor:
                clauses.append(Clause.from_mongo(clause))

            return clauses

        except Exception as e:
            logger.error(f"Failed to get clauses for document {document_id}: {e}")
            raise

    async def get_clauses_by_user(self, user_id: str, limit: int = 100) -> List[Clause]:
        """Get clauses for a specific user"""
        try:
            cursor = self.clauses_collection.find(
                {"user_id": user_id}
            ).sort("sequence_number", 1).limit(limit)

            clauses = []
            async for clause in cursor:
                clauses.append(Clause.from_mongo(clause))

            return clauses

        except Exception as e:
            logger.error(f"Failed to get clauses for user {user_id}: {e}")
            raise

    async def update_clause(self, clause_id: str, update_data: ClauseUpdate) -> bool:
        """Update clause"""
        try:
            update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
            if not update_dict:
                return False

            result = await self.clauses_collection.update_one(
                {"clause_id": clause_id},
                {"$set": update_dict}
            )

            success = result.modified_count > 0
            if success:
                logger.info(f"Updated clause: {clause_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to update clause {clause_id}: {e}")
            raise

    async def delete_clause(self, clause_id: str) -> bool:
        """Delete clause"""
        try:
            result = await self.clauses_collection.delete_one({"clause_id": clause_id})
            success = result.deleted_count > 0

            if success:
                logger.info(f"Deleted clause: {clause_id}")

            return success

        except Exception as e:
            logger.error(f"Failed to delete clause {clause_id}: {e}")
            raise

    async def get_clauses_by_type(self, clause_type: str, limit: int = 50) -> List[Clause]:
        """Get clauses by type"""
        try:
            cursor = self.clauses_collection.find(
                {"clause_type": clause_type}
            ).limit(limit)

            clauses = []
            async for clause in cursor:
                clauses.append(Clause.from_mongo(clause))

            return clauses

        except Exception as e:
            logger.error(f"Failed to get clauses by type {clause_type}: {e}")
            raise

    async def get_clauses_by_severity(self, min_severity: int = 4, limit: int = 100) -> List[Clause]:
        """Get high-severity clauses"""
        try:
            cursor = self.clauses_collection.find(
                {"severity_level": {"$gte": min_severity}}
            ).sort("severity_level", -1).limit(limit)

            clauses = []
            async for clause in cursor:
                clauses.append(Clause.from_mongo(clause))

            return clauses

        except Exception as e:
            logger.error(f"Failed to get clauses by severity {min_severity}: {e}")
            raise

    # Analytics and reporting
    async def get_document_stats(self) -> Dict[str, Any]:
        """Get overall document statistics"""
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": "$processing_status",
                        "count": {"$sum": 1}
                    }
                }
            ]

            status_stats = {}
            async for stat in self.documents_collection.aggregate(pipeline):
                status_stats[stat["_id"]] = stat["count"]

            total_docs = await self.documents_collection.count_documents({})

            return {
                "total_documents": total_docs,
                "status_breakdown": status_stats
            }

        except Exception as e:
            logger.error(f"Failed to get document stats: {e}")
            raise

    async def get_clause_stats(self) -> Dict[str, Any]:
        """Get overall clause statistics"""
        try:
            # Severity distribution
            severity_pipeline = [
                {
                    "$group": {
                        "_id": "$severity_level",
                        "count": {"$sum": 1}
                    }
                }
            ]

            severity_stats = {}
            async for stat in self.clauses_collection.aggregate(severity_pipeline):
                severity_stats[stat["_id"]] = stat["count"]

            # Type distribution
            type_pipeline = [
                {
                    "$group": {
                        "_id": "$clause_type",
                        "count": {"$sum": 1}
                    }
                }
            ]

            type_stats = {}
            async for stat in self.clauses_collection.aggregate(type_pipeline):
                type_stats[stat["_id"]] = stat["count"]

            total_clauses = await self.clauses_collection.count_documents({})

            return {
                "total_clauses": total_clauses,
                "severity_distribution": severity_stats,
                "type_distribution": type_stats
            }

        except Exception as e:
            logger.error(f"Failed to get clause stats: {e}")
            raise

# Global service instance
mongodb_service = MongoDBService()
