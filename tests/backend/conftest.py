import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from app.core.db import get_db
from app.main import app


@pytest_asyncio.fixture
async def db():
    """Isolated mongomock database per test, injected in place of a real MongoDB connection."""
    database = AsyncMongoMockClient()["asbo_test"]
    app.dependency_overrides[get_db] = lambda: database
    yield database
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def client(db):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
