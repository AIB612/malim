"""
Health Check API
System health and readiness endpoints
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..adapters import get_vector_store
from ..config import get_settings

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    app_name: str
    version: str
    vector_store: str
    vector_store_healthy: bool
    data_region: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Check application health status.
    
    Returns system status including:
    - Application info
    - Vector store connectivity
    - Data region (Swiss compliance)
    """
    settings = get_settings()
    vector_store = get_vector_store()
    
    # Check vector store health
    vs_healthy = await vector_store.health_check()
    
    return HealthResponse(
        status="healthy" if vs_healthy else "degraded",
        app_name=settings.app_name,
        version="0.1.0",
        vector_store=settings.vector_store.value,
        vector_store_healthy=vs_healthy,
        data_region=settings.data_region
    )


@router.get("/ready")
async def readiness_check():
    """
    Kubernetes readiness probe.
    Returns 200 if ready to accept traffic.
    """
    vector_store = get_vector_store()
    
    if not await vector_store.health_check():
        raise HTTPException(status_code=503, detail="Vector store not ready")
    
    return {"ready": True}


@router.get("/live")
async def liveness_check():
    """
    Kubernetes liveness probe.
    Returns 200 if application is alive.
    """
    return {"alive": True}
