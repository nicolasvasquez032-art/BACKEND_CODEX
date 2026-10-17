"""Pruebas unitarias y de integración para Rate Limiting en endpoints sensibles."""

from unittest.mock import AsyncMock, MagicMock
import pytest
from httpx import ASGITransport, AsyncClient

from infrastructure.adapters.persistence.database import get_read_session, get_session
from infrastructure.api.app import create_app
from infrastructure.api.rate_limiter import limiter


@pytest.fixture
def app_with_mocked_db():
    app = create_app()
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_read_session] = lambda: mock_session
    # Reset limiter storage before each test
    limiter.reset()
    return app


@pytest.mark.asyncio
async def test_login_rate_limiting_enforces_limit(app_with_mocked_db):
    """Verifica que /auth/login bloquee tras 5 intentos por minuto (límite: 5/minute)."""
    transport = ASGITransport(app=app_with_mocked_db)
    client_ip = "192.168.1.50"
    headers = {"X-Forwarded-For": client_ip}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Primeros 5 intentos deben llegar al caso de uso (401 credenciales inválidas)
        for _ in range(5):
            res = await client.post(
                "/auth/login",
                json={"email": "attacker@example.com", "password": "wrongpassword"},
                headers=headers,
            )
            assert res.status_code == 401

        # El 6to intento debe ser bloqueado con 429 Too Many Requests
        res_blocked = await client.post(
            "/auth/login",
            json={"email": "attacker@example.com", "password": "wrongpassword"},
            headers=headers,
        )
        assert res_blocked.status_code == 429
        data = res_blocked.json()
        assert "detail" in data
        assert "Demasiados intentos" in data["detail"]
        assert "Rate limit exceeded" in data["error"]


@pytest.mark.asyncio
async def test_recuperar_password_rate_limiting_with_i18n(app_with_mocked_db):
    """Verifica que /auth/recuperar-password limite a 3/minuto y responda en inglés si se solicita."""
    transport = ASGITransport(app=app_with_mocked_db)
    client_ip = "192.168.1.60"
    headers_es = {"X-Forwarded-For": client_ip, "Accept-Language": "es"}
    headers_en = {"X-Forwarded-For": client_ip, "Accept-Language": "en"}

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Primeros 3 intentos son aceptados (202)
        for _ in range(3):
            res = await client.post(
                "/auth/recuperar-password",
                json={"email": "victim@example.com"},
                headers=headers_es,
            )
            assert res.status_code == 202

        # 4to intento: Bloqueado (429) con traducción al inglés
        res_blocked_en = await client.post(
            "/auth/recuperar-password",
            json={"email": "victim@example.com"},
            headers=headers_en,
        )
        assert res_blocked_en.status_code == 429
        data_en = res_blocked_en.json()
        assert data_en["detail"] == "Too many requests. Please wait a moment before trying again."


@pytest.mark.asyncio
async def test_x_forwarded_for_client_ip_isolation(app_with_mocked_db):
    """Verifica que usuarios legítimos con IPs distintas no sean bloqueados por un atacante."""
    transport = ASGITransport(app=app_with_mocked_db)
    attacker_ip = "203.0.113.10"
    legitimate_ip = "203.0.113.20"

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # El atacante agota su límite de 5 intentos
        for _ in range(5):
            await client.post(
                "/auth/login",
                json={"email": "test@example.com", "password": "wrong"},
                headers={"X-Forwarded-For": attacker_ip},
            )

        # El atacante está bloqueado
        attacker_res = await client.post(
            "/auth/login",
            json={"email": "test@example.com", "password": "wrong"},
            headers={"X-Forwarded-For": attacker_ip},
        )
        assert attacker_res.status_code == 429

        # El usuario legítimo con otra IP NO debe estar bloqueado
        legit_res = await client.post(
            "/auth/login",
            json={"email": "legit@example.com", "password": "wrong"},
            headers={"X-Forwarded-For": legitimate_ip},
        )
        assert legit_res.status_code == 401
