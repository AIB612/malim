"""
PostgreSQL + pgvector Adapter for Malim
Self-hosted vector storage for private deployment
"""
import json
import logging
from datetime import datetime
from typing import List, Optional
from contextlib import asynccontextmanager

from sqlalchemy import text, Column, String, DateTime, Text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from .base import VectorStoreAdapter, Document, SearchResult
from ..config import get_settings

logger = logging.getLogger(__name__)

Base = declarative_base()


class PgVectorAdapter(VectorStoreAdapter):
    """
    PostgreSQL + pgvector implementation for vector storage.
    
    Ideal for:
    - Private/self-hosted deployments
    - Full data control
    - Cost-effective solution
    - Swiss data sovereignty requirements
    
    Features:
    - pgvector extension for vector similarity search
    - IVFFlat or HNSW indexing
    - Full SQL capabilities for complex queries
    - ACID compliance
    """
    
    VECTOR_DIMENSIONS = 1536  # OpenAI ada-002 embedding size
    TABLE_NAME = "malim_documents"
    
    def __init__(self):
        self.settings = get_settings()
        self.engine = None
        self.async_session = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize PostgreSQL connection and create tables"""
        if self._initialized:
            return
        
        # Create async engine
        self.engine = create_async_engine(
            self.settings.database_url,
            echo=self.settings.debug,
            pool_size=5,
            max_overflow=10
        )
        
        # Create session factory
        self.async_session = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        # Initialize pgvector extension and create table
        async with self.engine.begin() as conn:
            # Enable pgvector extension
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            
            # Create documents table
            await conn.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {self.TABLE_NAME} (
                    id VARCHAR(255) PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding vector({self.VECTOR_DIMENSIONS}),
                    vehicle_id VARCHAR(255),
                    doc_type VARCHAR(100),
                    metadata JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                )
            """))
            
            # Create vector index (IVFFlat for faster queries)
            await conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS {self.TABLE_NAME}_embedding_idx 
                ON {self.TABLE_NAME} 
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """))
            
            # Create metadata indexes
            await conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS {self.TABLE_NAME}_vehicle_idx 
                ON {self.TABLE_NAME} (vehicle_id)
            """))
            await conn.execute(text(f"""
                CREATE INDEX IF NOT EXISTS {self.TABLE_NAME}_doc_type_idx 
                ON {self.TABLE_NAME} (doc_type)
            """))
        
        self._initialized = True
        logger.info("pgvector adapter initialized")
    
    @asynccontextmanager
    async def _get_session(self):
        """Get async session context manager"""
        if not self.async_session:
            raise RuntimeError("Adapter not initialized")
        
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    async def add_documents(self, documents: List[Document]) -> List[str]:
        """Add documents to PostgreSQL"""
        added_ids = []
        
        async with self._get_session() as session:
            for doc in documents:
                # Convert embedding to pgvector format
                embedding_str = f"[{','.join(map(str, doc.embedding))}]" if doc.embedding else None
                
                # Prepare metadata
                metadata_json = json.dumps(doc.metadata) if doc.metadata else "{}"
                vehicle_id = doc.metadata.get("vehicle_id") if doc.metadata else None
                doc_type = doc.metadata.get("doc_type") if doc.metadata else None
                
                # Upsert document
                await session.execute(text(f"""
                    INSERT INTO {self.TABLE_NAME} 
                    (id, content, embedding, vehicle_id, doc_type, metadata, created_at, updated_at)
                    VALUES (:id, :content, :embedding::vector, :vehicle_id, :doc_type, :metadata::jsonb, NOW(), NOW())
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        vehicle_id = EXCLUDED.vehicle_id,
                        doc_type = EXCLUDED.doc_type,
                        metadata = EXCLUDED.metadata,
                        updated_at = NOW()
                """), {
                    "id": doc.id,
                    "content": doc.content,
                    "embedding": embedding_str,
                    "vehicle_id": vehicle_id,
                    "doc_type": doc_type,
                    "metadata": metadata_json
                })
                added_ids.append(doc.id)
        
        logger.info(f"Added {len(added_ids)} documents to pgvector")
        return added_ids
    
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter_metadata: Optional[dict] = None
    ) -> SearchResult:
        """Search for similar documents using cosine similarity"""
        # Build embedding string
        embedding_str = f"[{','.join(map(str, query_embedding))}]"
        
        # Build WHERE clause
        where_clauses = []
        params = {"embedding": embedding_str, "top_k": top_k}
        
        if filter_metadata:
            if "vehicle_id" in filter_metadata:
                where_clauses.append("vehicle_id = :vehicle_id")
                params["vehicle_id"] = filter_metadata["vehicle_id"]
            if "doc_type" in filter_metadata:
                where_clauses.append("doc_type = :doc_type")
                params["doc_type"] = filter_metadata["doc_type"]
        
        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        
        # Execute vector similarity search
        async with self._get_session() as session:
            result = await session.execute(text(f"""
                SELECT 
                    id, 
                    content, 
                    vehicle_id, 
                    doc_type, 
                    metadata,
                    1 - (embedding <=> :embedding::vector) as score
                FROM {self.TABLE_NAME}
                {where_sql}
                ORDER BY embedding <=> :embedding::vector
                LIMIT :top_k
            """), params)
            
            rows = result.fetchall()
        
        # Convert to Document objects
        documents = []
        for row in rows:
            doc = Document(
                id=row.id,
                content=row.content,
                score=float(row.score) if row.score else None,
                metadata={
                    "vehicle_id": row.vehicle_id,
                    "doc_type": row.doc_type,
                    **(json.loads(row.metadata) if row.metadata else {})
                }
            )
            documents.append(doc)
        
        return SearchResult(documents=documents, total_count=len(documents))
    
    async def delete_documents(self, document_ids: List[str]) -> int:
        """Delete documents by ID"""
        async with self._get_session() as session:
            result = await session.execute(text(f"""
                DELETE FROM {self.TABLE_NAME}
                WHERE id = ANY(:ids)
            """), {"ids": document_ids})
            
            deleted_count = result.rowcount
        
        logger.info(f"Deleted {deleted_count} documents from pgvector")
        return deleted_count
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Get a single document by ID"""
        async with self._get_session() as session:
            result = await session.execute(text(f"""
                SELECT id, content, vehicle_id, doc_type, metadata
                FROM {self.TABLE_NAME}
                WHERE id = :id
            """), {"id": document_id})
            
            row = result.fetchone()
        
        if not row:
            return None
        
        return Document(
            id=row.id,
            content=row.content,
            metadata={
                "vehicle_id": row.vehicle_id,
                "doc_type": row.doc_type,
                **(json.loads(row.metadata) if row.metadata else {})
            }
        )
    
    async def health_check(self) -> bool:
        """Check PostgreSQL connectivity"""
        if not self.engine:
            return False
        
        try:
            async with self._get_session() as session:
                await session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"pgvector health check failed: {e}")
            return False
    
    async def close(self) -> None:
        """Close PostgreSQL connections"""
        if self.engine:
            await self.engine.dispose()
        
        self.engine = None
        self.async_session = None
        self._initialized = False
        logger.info("pgvector adapter closed")
