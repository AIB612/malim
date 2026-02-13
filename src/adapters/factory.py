"""
Vector Store Factory
Plug & Play factory for creating the appropriate vector store adapter
"""
import logging
from typing import Optional

from .base import VectorStoreAdapter
from .pgvector import PgVectorAdapter
from ..config import get_settings, VectorStoreType

logger = logging.getLogger(__name__)

# Singleton instance
_vector_store_instance: Optional[VectorStoreAdapter] = None


def get_vector_store() -> VectorStoreAdapter:
    """
    Factory function to get the configured vector store adapter.
    
    Uses the VECTOR_STORE environment variable to determine which
    implementation to use:
    - "azure": Azure AI Search (Switzerland North)
    - "pgvector": PostgreSQL + pgvector (self-hosted)
    
    Returns a singleton instance for the application lifecycle.
    """
    global _vector_store_instance
    
    if _vector_store_instance is not None:
        return _vector_store_instance
    
    settings = get_settings()
    
    if settings.vector_store == VectorStoreType.AZURE:
        try:
            from .azure_search import AzureSearchAdapter
            logger.info("Creating Azure AI Search adapter (Switzerland North)")
            _vector_store_instance = AzureSearchAdapter()
        except ImportError:
            raise ImportError(
                "Azure Search adapter requires azure-search-documents. "
                "Install with: pip install azure-search-documents azure-identity"
            )
    
    elif settings.vector_store == VectorStoreType.PGVECTOR:
        logger.info("Creating pgvector adapter (self-hosted)")
        _vector_store_instance = PgVectorAdapter()
    
    else:
        raise ValueError(f"Unknown vector store type: {settings.vector_store}")
    
    return _vector_store_instance


async def reset_vector_store() -> None:
    """Reset the vector store singleton."""
    global _vector_store_instance
    
    if _vector_store_instance is not None:
        await _vector_store_instance.close()
        _vector_store_instance = None
        logger.info("Vector store instance reset")
