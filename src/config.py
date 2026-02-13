"""
Malim Configuration Management
Plug & Play configuration for Vector Store and LLM providers
"""
from enum import Enum
from functools import lru_cache
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class VectorStoreType(str, Enum):
    AZURE = "azure"
    PGVECTOR = "pgvector"


class LLMProviderType(str, Enum):
    AZURE = "azure"
    OPENAI = "openai"
    OLLAMA = "ollama"


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    app_name: str = "Malim"
    app_env: str = "development"
    debug: bool = True
    secret_key: str = "change-me-in-production"
    
    # Vector Store Selection (Plug & Play)
    vector_store: VectorStoreType = VectorStoreType.PGVECTOR
    
    # Azure AI Search (Switzerland North)
    azure_search_endpoint: Optional[str] = None
    azure_search_key: Optional[str] = None
    azure_search_index: str = "malim-vectors"
    
    # PostgreSQL + pgvector (individual params or DATABASE_URL)
    database_url_override: Optional[str] = Field(default=None, alias="DATABASE_URL")
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "malim"
    postgres_user: str = "malim"
    postgres_password: str = ""
    
    # LLM Provider Selection (Plug & Play)
    llm_provider: LLMProviderType = LLMProviderType.AZURE
    
    # Azure OpenAI
    azure_openai_endpoint: Optional[str] = None
    azure_openai_key: Optional[str] = None
    azure_openai_deployment: str = "gpt-4"
    azure_openai_embedding_deployment: str = "text-embedding-ada-002"
    
    # OpenAI
    openai_api_key: Optional[str] = None
    
    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama2"
    
    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"
    
    # Reports
    report_storage_path: str = "./reports"
    report_template_path: str = "./src/reports/templates"
    
    # Swiss Compliance
    data_region: str = "switzerland-north"
    enable_audit_log: bool = True
    
    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection URL"""
        if self.database_url_override:
            # Convert postgres:// to postgresql+asyncpg://
            url = self.database_url_override
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql+asyncpg://", 1)
            elif url.startswith("postgresql://"):
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
            return url
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def sync_database_url(self) -> str:
        """Construct sync PostgreSQL connection URL"""
        if self.database_url_override:
            url = self.database_url_override
            if url.startswith("postgres://"):
                url = url.replace("postgres://", "postgresql://", 1)
            return url
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
