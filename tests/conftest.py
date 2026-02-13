"""
Pytest configuration
"""
import pytest
import asyncio
from typing import Generator


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
def env_setup(monkeypatch):
    """Set up test environment variables"""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("VECTOR_STORE", "memory")
    monkeypatch.setenv("DEBUG", "false")
