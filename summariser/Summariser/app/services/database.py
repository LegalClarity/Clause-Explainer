"""
Database service for MongoDB operations
"""

import hashlib
from datetime import datetime, timedelta
from typing import Optional, List
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from loguru import logger

from ..config import settings
from ..models.schemas import DocumentSummaryDocument, AudioSummaryDocument


class DatabaseService:
    """Service for handling MongoDB operations"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.database: Optional[AsyncIOMotorDatabase] = None
        self.document_summaries: Optional[AsyncIOMotorCollection] = None
        self.audio_summaries: Optional[AsyncIOMotorCollection] = None
    
    async def connect(self):
        """Establish database connection"""
        try:
            self.client = AsyncIOMotorClient(settings.mongodb_connection_string)
            self.database = self.client[settings.mongodb_database_name]
            self.document_summaries = self.database.document_summaries
            self.audio_summaries = self.database.audio_summaries
            
            # Create indexes for better performance
            await self._create_indexes()
            
            # Test connection
            await self.client.admin.command('ping')
            logger.info("Successfully connected to MongoDB")
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise
    
    async def disconnect(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")
    
    async def _create_indexes(self):
        """Create database indexes for optimal performance"""
        try:
            # Document summaries indexes
            await self.document_summaries.create_index("document_hash", unique=True)
            await self.document_summaries.create_index("processed_timestamp")
            await self.document_summaries.create_index("filename")
            await self.document_summaries.create_index("file_type")
            
            # Audio summaries indexes
            await self.audio_summaries.create_index("audio_hash", unique=True)
            await self.audio_summaries.create_index("processed_timestamp")
            await self.audio_summaries.create_index("filename")
            await self.audio_summaries.create_index("session_type")
            await self.audio_summaries.create_index("duration_seconds")
            
            logger.info("Database indexes created successfully")
            
        except Exception as e:
            logger.warning(f"Failed to create some indexes: {e}")
    
    @staticmethod
    def generate_file_hash(file_content: bytes) -> str:
        """Generate SHA-256 hash for file content"""
        return hashlib.sha256(file_content).hexdigest()
    
    async def get_document_summary_by_hash(self, file_hash: str) -> Optional[DocumentSummaryDocument]:
        """Retrieve cached document summary by file hash"""
        if not settings.enable_caching:
            return None
            
        try:
            # Check if cache is still valid
            cutoff_time = datetime.utcnow() - timedelta(hours=settings.cache_ttl_hours)
            
            result = await self.document_summaries.find_one({
                "document_hash": file_hash,
                "processed_timestamp": {"$gte": cutoff_time}
            })
            
            if result:
                logger.info(f"Found cached document summary for hash: {file_hash}")
                return DocumentSummaryDocument(**result)
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving document summary: {e}")
            return None
    
    async def get_audio_summary_by_hash(self, file_hash: str) -> Optional[AudioSummaryDocument]:
        """Retrieve cached audio summary by file hash"""
        if not settings.enable_caching:
            return None
            
        try:
            # Check if cache is still valid
            cutoff_time = datetime.utcnow() - timedelta(hours=settings.cache_ttl_hours)
            
            result = await self.audio_summaries.find_one({
                "audio_hash": file_hash,
                "processed_timestamp": {"$gte": cutoff_time}
            })
            
            if result:
                logger.info(f"Found cached audio summary for hash: {file_hash}")
                return AudioSummaryDocument(**result)
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving audio summary: {e}")
            return None
    
    async def save_document_summary(self, summary_doc: DocumentSummaryDocument) -> str:
        """Save document summary to database"""
        if not settings.enable_caching:
            return "caching_disabled"
            
        try:
            # Use upsert to handle duplicate keys gracefully
            filter_criteria = {"document_hash": summary_doc.document_hash}
            update_data = {"$set": summary_doc.dict(by_alias=True, exclude={'id'})}
            
            result = await self.document_summaries.update_one(
                filter_criteria, 
                update_data, 
                upsert=True
            )
            
            if result.upserted_id:
                logger.info(f"Inserted new document summary with ID: {result.upserted_id}")
                return str(result.upserted_id)
            else:
                logger.info(f"Updated existing document summary for hash: {summary_doc.document_hash}")
                return "updated"
            
        except Exception as e:
            logger.error(f"Error saving document summary: {e}")
            raise
    
    async def save_audio_summary(self, summary_doc: AudioSummaryDocument) -> str:
        """Save audio summary to database"""
        if not settings.enable_caching:
            return "caching_disabled"
            
        try:
            # Use upsert to handle duplicate keys gracefully
            filter_criteria = {"audio_hash": summary_doc.audio_hash}
            update_data = {"$set": summary_doc.dict(by_alias=True, exclude={'id'})}
            
            result = await self.audio_summaries.update_one(
                filter_criteria, 
                update_data, 
                upsert=True
            )
            
            if result.upserted_id:
                logger.info(f"Inserted new audio summary with ID: {result.upserted_id}")
                return str(result.upserted_id)
            else:
                logger.info(f"Updated existing audio summary for hash: {summary_doc.audio_hash}")
                return "updated"
            
        except Exception as e:
            logger.error(f"Error saving audio summary: {e}")
            raise
    
    async def get_recent_document_summaries(self, limit: int = 10) -> List[DocumentSummaryDocument]:
        """Get recently processed document summaries"""
        try:
            cursor = self.document_summaries.find().sort("processed_timestamp", -1).limit(limit)
            results = []
            async for doc in cursor:
                results.append(DocumentSummaryDocument(**doc))
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving recent document summaries: {e}")
            return []
    
    async def get_recent_audio_summaries(self, limit: int = 10) -> List[AudioSummaryDocument]:
        """Get recently processed audio summaries"""
        try:
            cursor = self.audio_summaries.find().sort("processed_timestamp", -1).limit(limit)
            results = []
            async for doc in cursor:
                results.append(AudioSummaryDocument(**doc))
            return results
            
        except Exception as e:
            logger.error(f"Error retrieving recent audio summaries: {e}")
            return []
    
    async def cleanup_old_summaries(self):
        """Clean up old cached summaries beyond TTL"""
        if not settings.enable_caching:
            return
            
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=settings.cache_ttl_hours * 2)
            
            # Delete old document summaries
            doc_result = await self.document_summaries.delete_many({
                "processed_timestamp": {"$lt": cutoff_time}
            })
            
            # Delete old audio summaries
            audio_result = await self.audio_summaries.delete_many({
                "processed_timestamp": {"$lt": cutoff_time}
            })
            
            logger.info(f"Cleaned up {doc_result.deleted_count} document summaries and {audio_result.deleted_count} audio summaries")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
    
    async def get_database_stats(self) -> dict:
        """Get database statistics"""
        try:
            stats = {}
            
            # Document summaries stats
            stats['document_summaries_count'] = await self.document_summaries.count_documents({})
            
            # Audio summaries stats
            stats['audio_summaries_count'] = await self.audio_summaries.count_documents({})
            
            # Database size
            db_stats = await self.database.command("dbStats")
            stats['database_size_bytes'] = db_stats.get('dataSize', 0)
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting database stats: {e}")
            return {}


# Global database service instance
db_service = DatabaseService()
