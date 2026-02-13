"""
Abstract Base Class for Vector Store Adapters
Defines the interface that all vector stores must implement
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Document:
    """Represents a document with its embedding"""
    id: str
    content: str
    embedding: Optional[List[float]] = None
    metadata: Optional[dict] = None
    score: Optional[float] = None


@dataclass
class SearchResult:
    """Search result with relevance score"""
    documents: List[Document]
    total_count: int


class VectorStoreAdapter(ABC):
    """
    Abstract base class for vector store implementations.
    
    Implement this interface to add support for new vector databases.
    Current implementations:
    - AzureSearchAdapter: Azure AI Search (Switzerland North)
    - PgVectorAdapter: PostgreSQL + pgvector (self-hosted)
    """
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        Initialize the vector store connection and create necessary indexes.
        Called once at application startup.
        """
        pass
    
    @abstractmethod
    async def add_documents(self, documents: List[Document]) -> List[str]:
        """
        Add documents with their embeddings to the vector store.
        
        Args:
            documents: List of Document objects with content and embeddings
            
        Returns:
            List of document IDs that were added
        """
        pass
    
    @abstractmethod
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter_metadata: Optional[dict] = None
    ) -> SearchResult:
        """
        Search for similar documents using vector similarity.
        
        Args:
            query_embedding: The query vector
            top_k: Number of results to return
            filter_metadata: Optional metadata filters
            
        Returns:
            SearchResult with matching documents and scores
        """
        pass
    
    @abstractmethod
    async def delete_documents(self, document_ids: List[str]) -> int:
        """
        Delete documents by their IDs.
        
        Args:
            document_ids: List of document IDs to delete
            
        Returns:
            Number of documents deleted
        """
        pass
    
    @abstractmethod
    async def get_document(self, document_id: str) -> Optional[Document]:
        """
        Retrieve a single document by ID.
        
        Args:
            document_id: The document ID
            
        Returns:
            Document if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the vector store is healthy and accessible.
        
        Returns:
            True if healthy, False otherwise
        """
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """
        Close connections and cleanup resources.
        Called at application shutdown.
        """
        pass
