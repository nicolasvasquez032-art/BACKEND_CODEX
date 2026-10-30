import asyncio
from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from infrastructure.adapters.storage.s3_file_storage import S3FileStorageAdapter


@pytest.mark.asyncio
async def test_s3_is_aws_configured():
    adapter = S3FileStorageAdapter()
    adapter._access_key = None
    adapter._secret_key = None
    assert adapter._is_aws_configured() is False

    adapter._access_key = "test_key"
    adapter._secret_key = "test_secret"
    assert adapter._is_aws_configured() is True


@pytest.mark.asyncio
async def test_s3_upload_file_local_fallback(tmp_path):
    adapter = S3FileStorageAdapter()
    adapter._local_storage_dir = tmp_path
    adapter._access_key = None
    adapter._secret_key = None

    file_bytes = b"sample pdf content for test"
    file_key = await adapter.upload_file(file_bytes, "my_resume.pdf", "application/pdf")

    assert file_key.startswith("cvs/")
    assert file_key.endswith("my_resume.pdf")
    
    saved_file = tmp_path / Path(file_key).name
    assert saved_file.exists()
    assert saved_file.read_bytes() == file_bytes


@pytest.mark.asyncio
async def test_s3_upload_file_aws_success():
    adapter = S3FileStorageAdapter()
    adapter._access_key = "fake_key"
    adapter._secret_key = "fake_secret"
    adapter._bucket = "test-bucket"

    mock_s3 = MagicMock()
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_s3

    with patch.dict("sys.modules", {"boto3": mock_boto3}):
        file_key = await adapter.upload_file(b"test data", "doc.pdf", "application/pdf")

    assert file_key.startswith("cvs/")
    mock_s3.put_object.assert_called_once()


@pytest.mark.asyncio
async def test_s3_upload_file_aws_error_fallback(tmp_path):
    adapter = S3FileStorageAdapter()
    adapter._local_storage_dir = tmp_path
    adapter._access_key = "fake_key"
    adapter._secret_key = "fake_secret"

    mock_s3 = MagicMock()
    mock_s3.put_object.side_effect = Exception("AWS Network Error")
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_s3

    with patch.dict("sys.modules", {"boto3": mock_boto3}):
        file_key = await adapter.upload_file(b"data with error", "cv_err.pdf", "application/pdf")

    assert file_key.startswith("cvs/")
    saved_file = tmp_path / Path(file_key).name
    assert saved_file.exists()


@pytest.mark.asyncio
async def test_s3_generate_presigned_url_local():
    adapter = S3FileStorageAdapter()
    adapter._access_key = None
    adapter._secret_key = None

    url = await adapter.generate_presigned_url("cvs/1234_resume.pdf")
    assert "/api/v1/cvs/download/1234_resume.pdf" in url


@pytest.mark.asyncio
async def test_s3_generate_presigned_url_aws_success():
    adapter = S3FileStorageAdapter()
    adapter._access_key = "fake_key"
    adapter._secret_key = "fake_secret"
    adapter._bucket = "test-bucket"

    mock_s3 = MagicMock()
    mock_s3.generate_presigned_url.return_value = "https://s3.amazonaws.com/test-bucket/cv.pdf?token=xyz"
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_s3

    with patch.dict("sys.modules", {"boto3": mock_boto3}):
        url = await adapter.generate_presigned_url("cvs/1234_resume.pdf")

    assert url == "https://s3.amazonaws.com/test-bucket/cv.pdf?token=xyz"


@pytest.mark.asyncio
async def test_s3_generate_presigned_url_aws_error():
    adapter = S3FileStorageAdapter()
    adapter._access_key = "fake_key"
    adapter._secret_key = "fake_secret"

    mock_s3 = MagicMock()
    mock_s3.generate_presigned_url.side_effect = Exception("S3 signing error")
    mock_boto3 = MagicMock()
    mock_boto3.client.return_value = mock_s3

    with patch.dict("sys.modules", {"boto3": mock_boto3}):
        url = await adapter.generate_presigned_url("cvs/1234_resume.pdf")

    assert "/api/v1/cvs/download/1234_resume.pdf" in url


@pytest.mark.asyncio
async def test_user_repository_update_cv_text_with_url():
    import uuid
    from unittest.mock import AsyncMock
    from infrastructure.adapters.persistence.models import CandidateProfileModel
    from infrastructure.adapters.persistence.user_repository import SqlAlchemyUserRepository

    mock_session = AsyncMock()
    fake_id = uuid.uuid4()
    mock_model = CandidateProfileModel(
        id=fake_id,
        user_id=uuid.uuid4(),
        full_name="Ana Lopez",
        skills=["Python"],
        experience_years=2,
        cv_text="old text",
        cv_file_url=None,
    )
    mock_session.get.return_value = mock_model
    repo = SqlAlchemyUserRepository(mock_session)
    result = await repo.update_cv_text(fake_id, "new cv text", "cvs/my_cv.pdf")

    assert result.cv_text == "new cv text"
    assert result.cv_file_url == "cvs/my_cv.pdf"

