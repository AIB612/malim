"""
Azure AI Search Adapter for Malim
Connects to Azure AI Search in Switzerland North for vector storage
"""
import logging
from typing import List, Optional

from azure.core.credentials import AzureKeyCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    SearchIndex,
    SearchField,
    SearchFieldDataType,
    VectorSearch,
    HnswAlgorithmConfiguration,
    VectorSearchProfile,
    SearchableField,
    SimpleField,
)
from azure.search.documents.models import VectorizedQuery

from .base import VectorStoreAdapter, Document, SearchResult
from ..config import get_settings

logger = logging.getLogger(__name__)


class AzureSearchAdapter(VectorStoreAdapter):
    """
    Azure AI Search implementation for vector storage.
    
    Designed for Switzerland North deployment to ensure Swiss data compliance.
    
    Features:
    - HNSW algorithm for fast approximate nearest neighbor search
    - Hybrid search (vector + keyword)
    - Metadata filtering
    - Enterprise-grade security and compliance
    """
    
    VECTOR_DIMENSIONS = 1536  # OpenAI ada-002 embedding size
    
    def __init__(self):
        self.settings = get_settings()
        self.index_client: Optional[SearchIndexClient] = None
        self.search_client: Optional[SearchClient] = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize Azure Search clients and create index if needed"""
        if self._initialized:
            return
            
        if not self.settings.azure_search_endpoint or not self.settings.azure_search_key:
            raise ValueError("Azure Search endpoint and key must be configured")
        
        credential = AzureKeyCredential(self.settings.azure_search_key)
        
        # Index management client
        self.index_client = SearchIndexClient(
            endpoint=self.settings.azure_search_endpoint,
            credential=credential
        )
        
        # Create index if it doesn't exist
        await self._create_index_if_not_exists()
        
        # Search client for document operations
        self.search_client = SearchClient(
            endpoint=self.settings.azure_search_endpoint,
            index_name=self.settings.azure_search_index,
            credential=credential
        )
        
        self._initialized = True
        logger.info(f"Azure Search adapter initialized: {self.settings.azure_search_index}")
    
    async def _create_index_if_not_exists(self) -> None:
        """Create the search index with vector configuration"""
        index_name = self.settings.azure_search_index
        
        # Check if index exists
        try:
            self.index_client.get_index(index_name)
            logger.info(f"Index '{index_name}' already exists")
            return
        except Exception:
            pass  # Index doesn't exist, create it
        
        # Define index schema
        fields = [
            SimpleField(
                name="id",
                type=SearchFieldDataType.String,
                key=True,
                filterable=True
            ),
            SearchableField(
                name="content",
                type=SearchFieldDataType.String,
                searchable=True
            ),
            SearchField(
                name="embedding",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                searchable=True,
                vector_search_dimensions=self.VECTOR_DIMENSIONS,
                vector_search_profile_name="malim-vector-profile"
            ),
            # Metadata fields for filtering
            SimpleField(
                name="vehicle_id",
                type=SearchFieldDataType.String,
                filterable=True
            ),
            SimpleField(
                name="doc_type",
                type=SearchFieldDataType.String,
                filterable=True,
                facetable=True
            ),
            SimpleField(
                name="created_at",
                type=SearchFieldDataType.DateTimeOffset,
                filterable=True,
                sortable=True
            ),
        ]
        
        # Vector search configuration (HNSW)
        vector_search = VectorSearch(
            algorithms=[
                HnswAlgorithmConfiguration(
                    name="malim-hnsw",
                    parameters={
                        "m": 4,
                        "efConstruction": 400,
                        "efSearch": 500,
                        "metric": "cosine"
                    }
                )
            ],
            profiles=[
                VectorSearchProfile(
                    name="malim-vector-profile",
                    algorithm_configuration_name="malim-hnsw"
                )
            ]
        )
        
        # Create index
        index = SearchIndex(
            name=index_name,
            fields=fields,
            vector_search=vector_search
        )
        
        self.index_client.create_index(index)
        logger.info(f"Created index '{index_name}' with vector search")
    
    async def add_documents(self, documents: List[Document]) -> List[str]:
        """Add documents to Azure Search"""
        if not self.search_client:
            raise RuntimeError("Adapter not initialized")
        
        # Convert to Azure format
        azure_docs = []
        for doc in documents:
            azure_doc = {
                "id": doc.id,
                "content": doc.content,
                "embedding": doc.embedding,
            }
            # Add metadata fields
            if doc.metadata:
                azure_doc.update({
                    "vehicle_id": doc.metadata.get("vehicle_id"),
                    "doc_type": doc.metadata.get("doc_type"),
                    "created_at": doc.metadata.get("created_at"),
                })
            azure_docs.append(azure_doc)
        
        # Upload documents
        result = self.search_client.upload_documents(documents=azure_docs)
        
        # Return IDs of successfully added documents
        added_ids = [r.key for r in result if r.succeeded]
        logger.info(f"Added {len(added_ids)} documents to Azure Search")
        return added_ids
    
    async def search(
        self,
        query_embedding: List[float],
        top_k: int = 10,
        filter_metadata: Optional[dict] = None
    ) -> SearchResult:
        """Search for similar documents using vector similarity"""
        if not self.search_client:
            raise RuntimeError("Adapter not initialized")
        
        # Build vector query
        vector_query = VectorizedQuery(
            vector=query_embedding,
            k_nearest_neighbors=top_k,
            fields="embedding"
        )
        
        # Build filter expression
        filter_expr = None
        if filter_metadata:
            filters = []
            if "vehicle_id" in filter_metadata:
                filters.append(f"vehicle_id eq '{filter_metadata['vehicle_id']}'")
            if "doc_type" in filter_metadata:
                filters.append(f"doc_type eq '{filter_metadata['doc_type']}'")
            if filters:
                filter_expr = " and ".join(filters)
        
        # Execute search
        results = self.search_client.search(
            search_text=None,
            vector_queries=[vector_query],
            filter=filter_expr,
            top=top_k,
            select=["id", "content", "vehicle_id", "doc_type", "created_at"]
        )
        
        # Convert results
        documents = []
        for result in results:
            doc = Document(
                id=result["id"],
                content=result["content"],
                score=result["@search.score"],
                metadata={
                    "vehicle_id": result.get("vehicle_id"),
                    "doc_type": result.get("doc_type"),
                    "created_at": result.get("created_at"),
                }
            )
            documents.append(doc)
        
        return SearchResult(documents=documents, total_count=len(documents))
    
    async def delete_documents(self, document_ids: List[str]) -> int:
        """Delete documents by ID"""
        if not self.search_client:
            raise RuntimeError("Adapter not initialized")
        
        docs_to_delete = [{"id": doc_id} for doc_id in document_ids]
        result = self.search_client.delete_documents(documents=docs_to_delete)
        
        deleted_count = sum(1 for r in result if r.succeeded)
        logger.info(f"Deleted {deleted_count} documents from Azure Search")
        return deleted_count
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """Get a single document by ID"""
        if not self.search_client:
            raise RuntimeError("Adapter not initialized")
        
        try:
            result = self.search_client.get_document(key=document_id)
            return Document(
                id=result["id"],
                content=result["content"],
                metadata={
                    "vehicle_id": result.get("vehicle_id"),
                    "doc_type": result.get("doc_type"),
                    "created_at": result.get("created_at"),
                }
            )
        except Exception:
            return None
    
    async def health_check(self) -> bool:
        """Check Azure Search connectivity"""
        if not self.index_client:
            return False
        
        try:
            self.index_client.get_index(self.settings.azure_search_index)
            return True
        except Exception as e:
            logger.error(f"Azure Search health check failed: {e}")
            return False
    
    async def close(self) -> None:
        """Close Azure Search clients"""
        self.search_client = None
        self.index_client = None
        self._initialized = False
        logger.info("Azure Search adapter closed")
