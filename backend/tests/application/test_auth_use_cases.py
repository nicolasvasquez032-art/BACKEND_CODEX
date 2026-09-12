from datetime import UTC, datetime
from uuid import uuid4

import pytest

from application.use_cases.login_user import LoginUserCommand, LoginUserUseCase
from application.use_cases.register_candidate import (
    RegisterCandidateCommand,
    RegisterCandidateUseCase,
)
from domain.entities.candidate_profile import CandidateProfile
from domain.entities.user import User, UserRole
from domain.exceptions import EmailAlreadyRegisteredError, InvalidCredentialsError


class FakePasswordHasher:
    def hash(self, password: str) -> str:
        return f"hashed:{password}"

    def verify(self, plain_password: str, password_hash: str) -> bool:
        return password_hash == self.hash(plain_password)


class FakeTokenService:
    def create_access_token(self, user: User) -> str:
        return f"token-for:{user.id}"


class FakeUserRepository:
    def __init__(self) -> None:
        self.users_by_email: dict[str, User] = {}
        self.profiles_by_user_id: dict[object, CandidateProfile] = {}

    async def find_by_email(self, email: str) -> User | None:
        return self.users_by_email.get(email)

    async def find_by_id(self, user_id):
        return next((user for user in self.users_by_email.values() if user.id == user_id), None)

    async def create_user(self, email: str, password_hash: str, role: UserRole) -> User:
        user = User(
            id=uuid4(),
            email=email,
            password_hash=password_hash,
            role=role,
            created_at=datetime.now(UTC),
        )
        self.users_by_email[email] = user
        return user

    async def create_candidate_profile(
        self,
        user_id,
        full_name: str,
        skills: list[str],
        experience_years: int,
        location: str | None,
        education: str | None,
    ) -> CandidateProfile:
        profile = CandidateProfile(
            id=uuid4(),
            user_id=user_id,
            full_name=full_name,
            skills=skills,
            experience_years=experience_years,
            location=location,
            education=education,
        )
        self.profiles_by_user_id[user_id] = profile
        return profile

    async def get_candidate_profile_by_user_id(self, user_id):
        return self.profiles_by_user_id.get(user_id)


@pytest.mark.asyncio
async def test_register_candidate_creates_user_and_profile() -> None:
    repository = FakeUserRepository()
    use_case = RegisterCandidateUseCase(repository, FakePasswordHasher())

    profile = await use_case.execute(
        RegisterCandidateCommand(
            email="ana@example.com",
            password="password123",
            full_name="Ana Perez",
            skills=["ventas", "atencion al cliente"],
            experience_years=1,
            location="Fusagasuga",
            education="Tecnico",
        )
    )

    user = await repository.find_by_email("ana@example.com")
    assert user is not None
    assert user.role == UserRole.CANDIDATE
    assert user.password_hash == "hashed:password123"
    assert profile.user_id == user.id
    assert profile.skills == ["ventas", "atencion al cliente"]


@pytest.mark.asyncio
async def test_register_candidate_rejects_duplicate_email() -> None:
    repository = FakeUserRepository()
    use_case = RegisterCandidateUseCase(repository, FakePasswordHasher())
    command = RegisterCandidateCommand(
        email="ana@example.com",
        password="password123",
        full_name="Ana Perez",
        skills=[],
        experience_years=0,
    )

    await use_case.execute(command)

    with pytest.raises(EmailAlreadyRegisteredError):
        await use_case.execute(command)


@pytest.mark.asyncio
async def test_login_returns_access_token_for_valid_credentials() -> None:
    repository = FakeUserRepository()
    await repository.create_user("ana@example.com", "hashed:password123", UserRole.CANDIDATE)
    use_case = LoginUserUseCase(repository, FakePasswordHasher(), FakeTokenService())

    result = await use_case.execute(LoginUserCommand("ana@example.com", "password123"))

    assert result.token_type == "bearer"
    assert result.access_token.startswith("token-for:")


@pytest.mark.asyncio
async def test_login_rejects_invalid_credentials() -> None:
    repository = FakeUserRepository()
    await repository.create_user("ana@example.com", "hashed:password123", UserRole.CANDIDATE)
    use_case = LoginUserUseCase(repository, FakePasswordHasher(), FakeTokenService())

    with pytest.raises(InvalidCredentialsError):
        await use_case.execute(LoginUserCommand("ana@example.com", "wrong-password"))

