"""Tests unitarios para RequestPasswordResetUseCase y ConfirmPasswordResetUseCase."""
import hashlib
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from application.use_cases.confirm_password_reset import (
    ConfirmPasswordResetCommand,
    ConfirmPasswordResetUseCase,
)
from application.use_cases.request_password_reset import (
    RequestPasswordResetCommand,
    RequestPasswordResetUseCase,
)
from domain.exceptions import InvalidResetTokenError
from tests.fakes import FakeEmailService, FakePasswordHasher, FakeUserRepository


@pytest.fixture()
def repo() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture()
def hasher() -> FakePasswordHasher:
    return FakePasswordHasher()


@pytest.fixture()
def email_service() -> FakeEmailService:
    return FakeEmailService()


# ── RequestPasswordReset ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_request_reset_sends_email_when_email_exists(repo, email_service, hasher):
    await repo.create_user(
        email="usuario@example.com",
        password_hash=hasher.hash("old_password"),
        role="candidate",
    )

    use_case = RequestPasswordResetUseCase(repo, email_service)
    await use_case.execute(
        RequestPasswordResetCommand(
            email="usuario@example.com",
            frontend_url="https://app.talentmatch.com",
        )
    )

    assert email_service.sent_count == 1
    assert "usuario@example.com" in email_service.last_recipient


@pytest.mark.asyncio
async def test_request_reset_silent_when_email_not_found(repo, email_service):
    """No debe lanzar excepción ni enviar correo si el email no existe."""
    use_case = RequestPasswordResetUseCase(repo, email_service)
    await use_case.execute(
        RequestPasswordResetCommand(
            email="noexiste@example.com",
            frontend_url="https://app.talentmatch.com",
        )
    )

    assert email_service.sent_count == 0


@pytest.mark.asyncio
async def test_request_reset_stores_token_hash(repo, email_service, hasher):
    await repo.create_user(
        email="save@example.com",
        password_hash=hasher.hash("pass"),
        role="candidate",
    )

    use_case = RequestPasswordResetUseCase(repo, email_service)
    await use_case.execute(
        RequestPasswordResetCommand(
            email="save@example.com",
            frontend_url="https://app.talentmatch.com",
        )
    )

    assert len(repo.reset_tokens) == 1


# ── ConfirmPasswordReset ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_confirm_reset_updates_password(repo, hasher, email_service):
    user = await repo.create_user(
        email="cambio@example.com",
        password_hash=hasher.hash("old_pass"),
        role="candidate",
    )

    raw_token = "valid_raw_token_xyz"
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    await repo.create_password_reset_token(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )

    use_case = ConfirmPasswordResetUseCase(repo, hasher)
    await use_case.execute(
        ConfirmPasswordResetCommand(raw_token=raw_token, new_password="new_secure_pass")
    )

    updated_user = await repo.find_by_id(user.id)
    assert updated_user.password_hash == hasher.hash("new_secure_pass")


@pytest.mark.asyncio
async def test_confirm_reset_invalid_token_raises(repo, hasher):
    use_case = ConfirmPasswordResetUseCase(repo, hasher)
    with pytest.raises(InvalidResetTokenError):
        await use_case.execute(
            ConfirmPasswordResetCommand(raw_token="invalid_token", new_password="new_pass_123")
        )


@pytest.mark.asyncio
async def test_confirm_reset_expired_token_raises(repo, hasher):
    user = await repo.create_user(
        email="expired@example.com",
        password_hash=hasher.hash("old"),
        role="candidate",
    )

    raw_token = "expired_token"
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    await repo.create_password_reset_token(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) - timedelta(hours=2),  # ya expiró
    )

    use_case = ConfirmPasswordResetUseCase(repo, hasher)
    with pytest.raises(InvalidResetTokenError):
        await use_case.execute(
            ConfirmPasswordResetCommand(raw_token=raw_token, new_password="new_pass")
        )


@pytest.mark.asyncio
async def test_confirm_reset_used_token_raises(repo, hasher):
    user = await repo.create_user(
        email="used@example.com",
        password_hash=hasher.hash("old"),
        role="candidate",
    )

    raw_token = "already_used_token"
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    token = await repo.create_password_reset_token(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    await repo.mark_token_used(token.id)

    use_case = ConfirmPasswordResetUseCase(repo, hasher)
    with pytest.raises(InvalidResetTokenError):
        await use_case.execute(
            ConfirmPasswordResetCommand(raw_token=raw_token, new_password="another_pass")
        )
