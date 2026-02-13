"""
Malim Vector Store Adapters
Plug & Play architecture for switching between Azure AI Search and pgvector
"""
from .base import VectorStoreAdapter, Document, SearchResult
from .pgvector import PgVectorAdapter
from .factory import get_vector_store

# Azure adapter is optional (requires azure-search-documents)
try:
    from .azure_search import AzureSearchAdapter
    _AZURE_AVAILABLE = True
except ImportError:
    AzureSearchAdapter = None
    _AZURE_AVAILABLE = False

__all__ = [
    "VectorStoreAdapter",
    "AzureSearchAdapter",
    "PgVectorAdapter",
    "get_vector_store",
    "Document",
    "SearchResult",
]
