"""Tests unitarios para LoginUserUseCase."""
import pytest

from application.use_cases.login_user import LoginUserCommand, LoginUserUseCase
from domain.exceptions import InvalidCredentialsError
from tests.fakes import FakePasswordHasher, FakeTokenService, FakeUserRepository


@pytest.fixture()
def repo() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture()
def hasher() -> FakePasswordHasher:
    return FakePasswordHasher()


@pytest.fixture()
def token_service() -> FakeTokenService:
    return FakeTokenService()


@pytest.mark.asyncio
async def test_login_success(repo, hasher, token_service):
    # Registrar un usuario manualmente en el fake repo
    await repo.create_user(
        email="test@example.com",
        password_hash=hasher.hash("correct_password"),
        role="candidate",
    )

    use_case = LoginUserUseCase(repo, hasher, token_service)
    result = await use_case.execute(
        LoginUserCommand(email="test@example.com", password="correct_password")
    )

    assert result.access_token is not None
    assert result.token_type == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password_raises(repo, hasher, token_service):
    await repo.create_user(
        email="test@example.com",
        password_hash=hasher.hash("correct_password"),
        role="candidate",
    )

    use_case = LoginUserUseCase(repo, hasher, token_service)
    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(
            LoginUserCommand(email="test@example.com", password="wrong_password")
        )


@pytest.mark.asyncio
async def test_login_nonexistent_email_raises(repo, hasher, token_service):
    use_case = LoginUserUseCase(repo, hasher, token_service)
    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(
            LoginUserCommand(email="noexiste@example.com", password="anypassword")
        )
