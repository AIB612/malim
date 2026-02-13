"""
API Router - connects all endpoints
"""
from fastapi import APIRouter

from .vehicles import router as vehicles_router
from .reports import router as reports_router
from .chat import router as chat_router
from .health import router as health_router

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(vehicles_router, tags=["Vehicles"])
api_router.include_router(reports_router, tags=["Reports"])
api_router.include_router(chat_router, tags=["Chat"])
