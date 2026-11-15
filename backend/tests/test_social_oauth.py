from datetime import UTC, datetime
import uuid
from unittest.mock import AsyncMock, patch
import pytest
from httpx import ASGITransport, AsyncClient

from domain.entities.user import User, UserRole
from infrastructure.adapters.persistence.database import get_session
from infrastructure.api.app import create_app


@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def app(mock_session):
    test_app = create_app()
    test_app.dependency_overrides[get_session] = lambda: mock_session
    return test_app


@pytest.mark.asyncio
async def test_oauth_config_endpoint(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/auth/oauth/config")
        assert resp.status_code == 200
        data = resp.json()
        assert "google_configured" in data
        assert "facebook_configured" in data
        assert "linkedin_configured" in data


@pytest.mark.asyncio
async def test_social_login_google_creates_user_and_returns_jwt(app, mock_session):
    transport = ASGITransport(app=app)
    user_id = uuid.uuid4()
    mock_user = User(
        id=user_id,
        email="google.user@example.com",
        password_hash="hashed_pw",
        role=UserRole.CANDIDATE,
        is_premium=False,
        created_at=datetime.now(UTC),
    )

    with patch(
        "infrastructure.adapters.persistence.user_repository.SqlAlchemyUserRepository.find_by_email",
        new_callable=AsyncMock,
    ) as mock_find, patch(
        "infrastructure.adapters.persistence.user_repository.SqlAlchemyUserRepository.create_user",
        new_callable=AsyncMock,
    ) as mock_create_user, patch(
        "infrastructure.adapters.persistence.user_repository.SqlAlchemyUserRepository.create_candidate_profile",
        new_callable=AsyncMock,
    ) as mock_create_profile:
        # First find returns None (new user), then create_user returns mock_user
        mock_find.return_value = None
        mock_create_user.return_value = mock_user

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "provider": "google",
                "token": "mock_google_token_123",
                "email": "google.user@example.com",
                "full_name": "Google User",
            }
            resp = await client.post("/auth/oauth/google", json=payload)
            assert resp.status_code == 200
            data = resp.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert "refresh_token" in data


@pytest.mark.asyncio
async def test_social_login_facebook_and_linkedin(app, mock_session):
    transport = ASGITransport(app=app)
    mock_user = User(
        id=uuid.uuid4(),
        email="social.user@example.com",
        password_hash="hashed_pw",
        role=UserRole.CANDIDATE,
        is_premium=False,
        created_at=datetime.now(UTC),
    )

    with patch(
        "infrastructure.adapters.persistence.user_repository.SqlAlchemyUserRepository.find_by_email",
        new_callable=AsyncMock,
    ) as mock_find, patch(
        "infrastructure.adapters.persistence.user_repository.SqlAlchemyUserRepository.create_user",
        new_callable=AsyncMock,
    ) as mock_create_user, patch(
        "infrastructure.adapters.persistence.user_repository.SqlAlchemyUserRepository.create_candidate_profile",
        new_callable=AsyncMock,
    ) as mock_create_profile:
        mock_find.return_value = mock_user

        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Facebook
            resp_fb = await client.post(
                "/auth/oauth/facebook",
                json={
                    "provider": "facebook",
                    "token": "mock_token_fb",
                    "email": "social.user@example.com",
                },
            )
            assert resp_fb.status_code == 200
            assert "access_token" in resp_fb.json()

            # LinkedIn
            resp_li = await client.post(
                "/auth/oauth/linkedin",
                json={
                    "provider": "linkedin",
                    "token": "mock_token_li",
                    "email": "social.user@example.com",
                },
            )
            assert resp_li.status_code == 200
            assert "access_token" in resp_li.json()


@pytest.mark.asyncio
async def test_social_login_invalid_provider_returns_400(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/auth/oauth/social",
            json={"provider": "github_disabled", "token": "abc"},
        )
        assert resp.status_code == 400
