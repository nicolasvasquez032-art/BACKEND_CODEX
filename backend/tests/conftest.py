import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from main import app  # Ajusta la ruta si 'app' está en otro lugar, por ejemplo 'infrastructure.api.app'


@pytest_asyncio.fixture(scope="session")
async def async_client():
    from infrastructure.api.app import create_app
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
