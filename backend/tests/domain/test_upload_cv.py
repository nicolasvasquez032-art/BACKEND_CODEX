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


@pytest.mark.asyncio
async def test_upload_cv_file_too_large_raises(repo_with_candidate):
    repo, user, profile = repo_with_candidate
    parser = FakeCvParser(extracted_text="some text")

    use_case = UploadCvUseCase(repo, parser, FakeMlService())
    large_bytes = b"0" * (10 * 1024 * 1024 + 1)
    with pytest.raises(CVProcessingError, match="El archivo no puede superar los 10 MB"):
        await use_case.execute(
            UploadCvCommand(
                profile_id=profile.id,
                requesting_user_id=user.id,
                file_bytes=large_bytes,
                mime_type="application/pdf",
            )
        )


class FakeStorage:
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail

    async def upload_file(self, file_bytes: bytes, file_name: str, content_type: str) -> str:
        if self.should_fail:
            raise RuntimeError("Storage upload failed")
        return f"cvs/stored_{file_name}"

    async def generate_presigned_url(self, file_key: str, expires_in_seconds: int = 900) -> str:
        return f"https://cdn.example.com/{file_key}"


@pytest.mark.asyncio
async def test_upload_cv_with_storage_success(repo_with_candidate):
    repo, user, profile = repo_with_candidate
    parser = FakeCvParser(extracted_text="Ingeniero de Software Senior")
    storage = FakeStorage()

    use_case = UploadCvUseCase(repo, parser, FakeMlService(), storage=storage)
    result = await use_case.execute(
        UploadCvCommand(
            profile_id=profile.id,
            requesting_user_id=user.id,
            file_bytes=b"pdf data",
            mime_type="application/pdf",
            file_name="cv_juan.pdf",
        )
    )

    assert result.cv_text == "Ingeniero de Software Senior"
    assert result.cv_file_url == "cvs/stored_cv_juan.pdf"


@pytest.mark.asyncio
async def test_upload_cv_with_storage_error_still_saves_text(repo_with_candidate):
    repo, user, profile = repo_with_candidate
    parser = FakeCvParser(extracted_text="Desarrollador Python")
    storage = FakeStorage(should_fail=True)

    use_case = UploadCvUseCase(repo, parser, FakeMlService(), storage=storage)
    result = await use_case.execute(
        UploadCvCommand(
            profile_id=profile.id,
            requesting_user_id=user.id,
            file_bytes=b"pdf data",
            mime_type="application/pdf",
            file_name="cv_err.pdf",
        )
    )

    assert result.cv_text == "Desarrollador Python"
    assert result.cv_file_url is None


class FakeMlServiceWithSchedule:
    def __init__(self):
        self.scheduled = []

    def schedule_embedding_update(self, profile_id, text):
        self.scheduled.append((profile_id, text))


@pytest.mark.asyncio
async def test_upload_cv_schedule_embedding(repo_with_candidate):
    repo, user, profile = repo_with_candidate
    parser = FakeCvParser(extracted_text="Especialista Cloud")
    ml_service = FakeMlServiceWithSchedule()

    use_case = UploadCvUseCase(repo, parser, ml_service)
    result = await use_case.execute(
        UploadCvCommand(
            profile_id=profile.id,
            requesting_user_id=user.id,
            file_bytes=b"pdf data",
            mime_type="application/pdf",
        )
    )

    assert result.cv_text == "Especialista Cloud"
    assert len(ml_service.scheduled) == 1

