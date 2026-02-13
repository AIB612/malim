"""
Malim FastAPI Application
Main entry point for the EV Battery Health Platform
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from .config import get_settings
from .adapters import get_vector_store
from .api import health, vehicles, reports, chat
from .db import init_db, close_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    settings = get_settings()
    logger.info(f"Starting {settings.app_name} in {settings.app_env} mode")
    
    # Initialize database
    try:
        await init_db()
        logger.info("Database connected")
    except Exception as e:
        logger.warning(f"Database connection failed: {e}")
    
    # Initialize vector store
    try:
        vector_store = get_vector_store()
        await vector_store.initialize()
        logger.info(f"Vector store initialized: {settings.vector_store}")
    except Exception as e:
        logger.warning(f"Vector store initialization failed: {e}")
    
    yield
    
    # Cleanup
    try:
        await close_db()
        vector_store = get_vector_store()
        await vector_store.close()
    except Exception:
        pass
    logger.info("Application shutdown complete")


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        description="EV Battery Health & Value Passport Platform",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(vehicles.router, prefix=settings.api_prefix, tags=["Vehicles"])
    app.include_router(reports.router, prefix=settings.api_prefix, tags=["Reports"])
    app.include_router(chat.router, prefix=settings.api_prefix, tags=["Chat"])
    
    # Static files
    static_path = Path(__file__).parent.parent / "static"
    if static_path.exists():
        app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
        
        @app.get("/")
        async def root():
            return FileResponse(str(static_path / "index.html"))
    else:
        @app.get("/")
        async def root():
            return {
                "name": "Malim API",
                "version": "0.1.0",
                "description": "🔋 EV Battery Health Platform",
                "made_in": "🇨🇭 Switzerland",
                "docs": "/docs",
                "health": "/live",
                "endpoints": {
                    "vehicles": "/api/v1/vehicles",
                    "reports": "/api/v1/reports",
                    "chat": "/api/v1/chat"
                }
            }
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run(
        "src.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )
