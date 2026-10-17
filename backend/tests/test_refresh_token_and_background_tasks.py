"""Tests para renovación de tokens (Refresh Token) y tareas asíncronas en segundo plano (BackgroundTasks)."""

import uuid
from unittest.mock import AsyncMock, MagicMock
import pytest
from httpx import ASGITransport, AsyncClient

from domain.entities.user import User, UserRole
from infrastructure.adapters.persistence.database import get_read_session, get_session
from infrastructure.adapters.security import JwtTokenService, PasslibPasswordHasher
from infrastructure.api.app import create_app
from infrastructure.api.rate_limiter import limiter


@pytest.fixture
def mock_db_with_user():
    app = create_app()
    from datetime import UTC, datetime
    hasher = PasslibPasswordHasher()
    hashed = hasher.hash("securepassword123")

    mock_session = AsyncMock()
    user_id = uuid.uuid4()
    user_model = MagicMock()
    user_model.id = user_id
    user_model.email = "refresh_test@example.com"
    user_model.password_hash = hashed
    user_model.role = UserRole.CANDIDATE
    user_model.is_premium = False
    user_model.created_at = datetime.now(UTC)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = user_model
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.get = AsyncMock(return_value=user_model)

    user = User(
        id=user_id,
        email="refresh_test@example.com",
        password_hash=hashed,
        role=UserRole.CANDIDATE,
        created_at=datetime.now(UTC),
        is_premium=False,
    )

    app.dependency_overrides[get_session] = lambda: mock_session
    app.dependency_overrides[get_read_session] = lambda: mock_session
    limiter.reset()
    return app, user


@pytest.mark.asyncio
async def test_login_returns_refresh_token(mock_db_with_user):
    """Verifica que el login retorne tanto access_token como refresh_token."""
    app, user = mock_db_with_user
    transport = ASGITransport(app=app)
    token_service = JwtTokenService()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/auth/login",
            json={"email": user.email, "password": "securepassword123"},
        )
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

        # Validar payloads decodificados
        access_payload = token_service.decode_token(data["access_token"])
        refresh_payload = token_service.decode_token(data["refresh_token"])

        assert access_payload["type"] == "access"
        assert refresh_payload["type"] == "refresh"
        assert access_payload["sub"] == str(user.id)
        assert refresh_payload["sub"] == str(user.id)


@pytest.mark.asyncio
async def test_refresh_token_flow(mock_db_with_user):
    """Verifica que POST /auth/refresh renueve exitosamente el par de tokens."""
    app, user = mock_db_with_user
    transport = ASGITransport(app=app)
    token_service = JwtTokenService()

    refresh_token = token_service.create_refresh_token(user)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert res.status_code == 200
        data = res.json()
        assert "access_token" in data
        assert "refresh_token" in data

        new_access = token_service.decode_token(data["access_token"])
        assert new_access["type"] == "access"
        assert new_access["sub"] == str(user.id)


@pytest.mark.asyncio
async def test_refresh_token_rejects_access_token_or_garbage(mock_db_with_user):
    """Verifica que no se pueda usar un access_token para refrescar la sesión."""
    app, user = mock_db_with_user
    transport = ASGITransport(app=app)
    token_service = JwtTokenService()

    access_token = token_service.create_access_token(user)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Enviar access_token en vez de refresh_token
        res = await client.post(
            "/auth/refresh",
            json={"refresh_token": access_token},
        )
        assert res.status_code == 401
        assert "no es un refresh token" in res.json()["detail"]

        # 2. Enviar token corrupto
        res_bad = await client.post(
            "/auth/refresh",
            json={"refresh_token": "token.invalido.123"},
        )
        assert res_bad.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_rejects_refresh_token(mock_db_with_user):
    """Verifica que un refresh_token no pueda ser usado como Bearer token para autenticar endpoints."""
    app, user = mock_db_with_user
    transport = ASGITransport(app=app)
    token_service = JwtTokenService()

    refresh_token = token_service.create_refresh_token(user)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(
            "/perfiles/me",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert res.status_code == 401


@pytest.mark.asyncio
async def test_password_reset_uses_background_tasks(mock_db_with_user):
    """Verifica que /auth/recuperar-password responda 202 de inmediato usando BackgroundTasks."""
    app, user = mock_db_with_user
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/auth/recuperar-password",
            json={"email": user.email},
        )
        assert res.status_code == 202
        assert "detail" in res.json()


def test_sentry_initialization_when_dsn_configured(monkeypatch):
    """Verifica que Sentry se inicialice correctamente cuando sentry_dsn está configurado."""
    from unittest.mock import patch
    from infrastructure.config import settings

    monkeypatch.setattr(settings, "sentry_dsn", "https://examplePublicKey@o0.ingest.sentry.io/0")
    monkeypatch.setattr(settings, "sentry_environment", "staging")

    with patch("sentry_sdk.init") as mock_sentry_init:
        create_app()
        mock_sentry_init.assert_called_once_with(
            dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
            environment="staging",
            traces_sample_rate=1.0,
            send_default_pii=False,
        )


@pytest.mark.asyncio
async def test_global_exception_handler_captures_sentry(mock_db_with_user, monkeypatch):
    """Verifica que las excepciones 500 no controladas se reporten a Sentry."""
    from unittest.mock import patch
    from infrastructure.config import settings

    app, _ = mock_db_with_user
    monkeypatch.setattr(settings, "sentry_dsn", "https://examplePublicKey@o0.ingest.sentry.io/0")

    # Agregar una ruta de prueba que lance una excepción no controlada
    @app.get("/test-error-500")
    async def error_route():
        raise RuntimeError("Prueba de fallo para Sentry")

    with patch("sentry_sdk.capture_exception") as mock_capture:
        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/test-error-500")
            assert res.status_code == 500
            assert mock_capture.called

