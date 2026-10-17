"""Pruebas unitarias para el servicio de caché distribuido con Redis y fallback."""
import pytest
from unittest.mock import AsyncMock, patch

from infrastructure.adapters.cache.redis_cache_service import RedisCacheService


@pytest.mark.asyncio
async def test_cache_service_fallback_when_disabled():
    """Verifica que si no hay Redis configurado, opera en fallback sin errores."""
    cache = RedisCacheService(redis_url=None)
    assert cache.is_available is False
    assert await cache.get("test_key") is None
    assert await cache.set("test_key", "value") is False
    assert await cache.get_json("test_key") is None
    assert await cache.set_json("test_key", {"foo": "bar"}) is False
    assert await cache.get_vacantes_version() == 1


@pytest.mark.asyncio
async def test_cache_service_operations_with_client():
    """Valida operaciones get, set y get_json contra el cliente de Redis."""
    cache = RedisCacheService(redis_url=None)
    mock_client = AsyncMock()
    mock_client.get.return_value = '{"titulo": "Ingeniero Software", "salario": 5000}'
    mock_client.set.return_value = True
    mock_client.incr.return_value = 2

    cache._client = mock_client
    cache._is_available = True

    data = await cache.get_json("vacantes:1")
    assert data is not None
    assert data["titulo"] == "Ingeniero Software"

    assert await cache.set_json("vacantes:1", data) is True
    mock_client.set.assert_called_once()

    await cache.invalidate_vacantes_cache()
    mock_client.incr.assert_called_once_with("vacantes:cache_version")
