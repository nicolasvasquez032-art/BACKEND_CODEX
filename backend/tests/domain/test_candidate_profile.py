"""Tests unitarios para UpdateCandidateProfileUseCase y GetCandidateProfileUseCase."""
import uuid

import pytest

from application.use_cases.get_candidate_profile import (
    GetCandidateProfileCommand,
    GetCandidateProfileUseCase,
)
from application.use_cases.update_candidate_profile import (
    UpdateCandidateProfileCommand,
    UpdateCandidateProfileUseCase,
)
from domain.exceptions import PermissionDeniedError, ProfileNotFoundError
from tests.fakes import FakePasswordHasher, FakeUserRepository


@pytest.fixture()
async def repo_with_candidate() -> tuple[FakeUserRepository, object, object]:
    """Devuelve (repo, user, profile) con un candidato ya registrado."""
    repo = FakeUserRepository()
    hasher = FakePasswordHasher()
    user = await repo.create_user(
        email="candi@example.com",
        password_hash=hasher.hash("pass"),
        role="candidate",
    )
    profile = await repo.create_candidate_profile(
        user_id=user.id,
        full_name="Carlos Ruiz",
        skills=["SQL", "Excel"],
        experience_years=1,
        location="Bogotá",
        education="Administración",
    )
    return repo, user, profile


# ── UpdateCandidateProfile ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_profile_success(repo_with_candidate):
    repo, user, profile = await repo_with_candidate
    use_case = UpdateCandidateProfileUseCase(repo)

    updated = await use_case.execute(
        UpdateCandidateProfileCommand(
            profile_id=profile.id,
            requesting_user_id=user.id,
            full_name="Carlos Ruiz Actualizado",
            skills=["SQL", "Excel", "Python"],
            experience_years=2,
            location="Medellín",
            education="MBA",
        )
    )

    assert updated.full_name == "Carlos Ruiz Actualizado"
    assert "Python" in updated.skills
    assert updated.experience_years == 2


@pytest.mark.asyncio
async def test_update_profile_not_owner_raises(repo_with_candidate):
    repo, user, profile = await repo_with_candidate
    other_user_id = uuid.uuid4()
    use_case = UpdateCandidateProfileUseCase(repo)

    with pytest.raises(PermissionDeniedError):
        await use_case.execute(
            UpdateCandidateProfileCommand(
                profile_id=profile.id,
                requesting_user_id=other_user_id,
                full_name="Hacker",
                skills=[],
                experience_years=0,
            )
        )


@pytest.mark.asyncio
async def test_update_profile_not_found_raises():
    repo = FakeUserRepository()
    use_case = UpdateCandidateProfileUseCase(repo)

    with pytest.raises(ProfileNotFoundError):
        await use_case.execute(
            UpdateCandidateProfileCommand(
                profile_id=uuid.uuid4(),
                requesting_user_id=uuid.uuid4(),
                full_name="Nobody",
                skills=[],
                experience_years=0,
            )
        )


# ── GetCandidateProfile ───────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_profile_owner_can_view(repo_with_candidate):
    repo, user, profile = await repo_with_candidate
    use_case = GetCandidateProfileUseCase(repo)

    result = await use_case.execute(
        GetCandidateProfileCommand(
            profile_id=profile.id,
            requesting_user_id=user.id,
            requesting_user_role="candidate",
        )
    )
    assert result.id == profile.id


@pytest.mark.asyncio
async def test_get_profile_another_candidate_denied(repo_with_candidate):
    repo, user, profile = await repo_with_candidate
    use_case = GetCandidateProfileUseCase(repo)

    with pytest.raises(PermissionDeniedError):
        await use_case.execute(
            GetCandidateProfileCommand(
                profile_id=profile.id,
                requesting_user_id=uuid.uuid4(),  # otro candidato
                requesting_user_role="candidate",
            )
        )


@pytest.mark.asyncio
async def test_get_profile_company_can_view_any(repo_with_candidate):
    repo, user, profile = await repo_with_candidate
    use_case = GetCandidateProfileUseCase(repo)

    result = await use_case.execute(
        GetCandidateProfileCommand(
            profile_id=profile.id,
            requesting_user_id=uuid.uuid4(),  # empresa cualquiera
            requesting_user_role="company",
        )
    )
    assert result.id == profile.id
