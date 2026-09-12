"""Tests unitarios para RegisterCandidateUseCase.

No se usa base de datos; el repositorio y el hasher son fakes en memoria.
"""
import pytest

from application.use_cases.register_candidate import (
    RegisterCandidateCommand,
    RegisterCandidateUseCase,
)
from domain.entities.candidate_profile import CandidateProfile
from domain.entities.user import User, UserRole
from domain.exceptions import EmailAlreadyRegisteredError
from tests.fakes import FakePasswordHasher, FakeUserRepository


@pytest.fixture()
def repo() -> FakeUserRepository:
    return FakeUserRepository()


@pytest.fixture()
def hasher() -> FakePasswordHasher:
    return FakePasswordHasher()


@pytest.mark.asyncio
async def test_register_candidate_success(repo, hasher):
    use_case = RegisterCandidateUseCase(repo, hasher)
    cmd = RegisterCandidateCommand(
        email="juan@example.com",
        password="securepass123",
        full_name="Juan Pérez",
        skills=["Python", "FastAPI"],
        experience_years=2,
        location="Fusagasugá",
        education="Ingeniería de Sistemas",
    )
    profile = await use_case.execute(cmd)

    assert isinstance(profile, CandidateProfile)
    assert profile.full_name == "Juan Pérez"
    assert profile.skills == ["Python", "FastAPI"]
    assert profile.experience_years == 2
    assert profile.location == "Fusagasugá"


@pytest.mark.asyncio
async def test_register_candidate_stores_hashed_password(repo, hasher):
    use_case = RegisterCandidateUseCase(repo, hasher)
    cmd = RegisterCandidateCommand(
        email="maria@example.com",
        password="mypassword",
        full_name="María García",
        skills=[],
        experience_years=0,
    )
    await use_case.execute(cmd)

    user: User = list(repo.users.values())[0]
    assert user.password_hash == hasher.hash("mypassword")
    assert user.role == UserRole.CANDIDATE


@pytest.mark.asyncio
async def test_register_candidate_duplicate_email_raises(repo, hasher):
    use_case = RegisterCandidateUseCase(repo, hasher)
    cmd = RegisterCandidateCommand(
        email="dup@example.com",
        password="pass1234",
        full_name="Dup User",
        skills=[],
        experience_years=0,
    )
    await use_case.execute(cmd)

    with pytest.raises(EmailAlreadyRegisteredError):
        await use_case.execute(cmd)
