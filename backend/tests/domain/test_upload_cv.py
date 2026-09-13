"""Tests unitarios para UploadCvUseCase."""
import uuid

import pytest

from application.use_cases.upload_cv import UploadCvCommand, UploadCvUseCase
from domain.exceptions import CVProcessingError, PermissionDeniedError, ProfileNotFoundError
from tests.fakes import FakeCvParser, FakeMlService, FakePasswordHasher, FakeUserRepository


@pytest.fixture()
async def repo_with_candidate():
    repo = FakeUserRepository()
    hasher = FakePasswordHasher()
    user = await repo.create_user(
        email="cv_user@example.com",
        password_hash=hasher.hash("pass"),
        role="candidate",
    )
    profile = await repo.create_candidate_profile(
        user_id=user.id,
        full_name="Laura Gómez",
        skills=["Diseño gráfico"],
        experience_years=3,
        location=None,
        education=None,
    )
    return repo, user, profile


@pytest.mark.asyncio
async def test_upload_cv_success(repo_with_candidate):
    repo, user, profile = repo_with_candidate
    parser = FakeCvParser(extracted_text="Experiencia: 3 años en diseño")

    use_case = UploadCvUseCase(repo, parser, FakeMlService())
    result = await use_case.execute(
        UploadCvCommand(
            profile_id=profile.id,
            requesting_user_id=user.id,
            file_bytes=b"%PDF-1.4 fake content",
            mime_type="application/pdf",
        )
    )

    assert result.cv_text == "Experiencia: 3 años en diseño"


@pytest.mark.asyncio
async def test_upload_cv_not_owner_raises(repo_with_candidate):
    repo, user, profile = repo_with_candidate
    parser = FakeCvParser(extracted_text="some text")

    use_case = UploadCvUseCase(repo, parser, FakeMlService())
    with pytest.raises(PermissionDeniedError):
        await use_case.execute(
            UploadCvCommand(
                profile_id=profile.id,
                requesting_user_id=uuid.uuid4(),
                file_bytes=b"content",
                mime_type="application/pdf",
            )
        )


@pytest.mark.asyncio
async def test_upload_cv_unsupported_mime_raises(repo_with_candidate):
    repo, user, profile = repo_with_candidate
    parser = FakeCvParser(extracted_text="some text")

    use_case = UploadCvUseCase(repo, parser, FakeMlService())
    with pytest.raises(CVProcessingError):
        await use_case.execute(
            UploadCvCommand(
                profile_id=profile.id,
                requesting_user_id=user.id,
                file_bytes=b"content",
                mime_type="application/zip",
            )
        )


@pytest.mark.asyncio
async def test_upload_cv_empty_extracted_text_raises(repo_with_candidate):
    repo, user, profile = repo_with_candidate
    parser = FakeCvParser(extracted_text="   ")  # solo espacios

    use_case = UploadCvUseCase(repo, parser, FakeMlService())
    with pytest.raises(CVProcessingError):
        await use_case.execute(
            UploadCvCommand(
                profile_id=profile.id,
                requesting_user_id=user.id,
                file_bytes=b"empty_pdf",
                mime_type="application/pdf",
            )
        )


@pytest.mark.asyncio
async def test_upload_cv_profile_not_found_raises():
    repo = FakeUserRepository()
    parser = FakeCvParser(extracted_text="text")

    use_case = UploadCvUseCase(repo, parser, FakeMlService())
    with pytest.raises(ProfileNotFoundError):
        await use_case.execute(
            UploadCvCommand(
                profile_id=uuid.uuid4(),
                requesting_user_id=uuid.uuid4(),
                file_bytes=b"content",
                mime_type="application/pdf",
            )
        )
