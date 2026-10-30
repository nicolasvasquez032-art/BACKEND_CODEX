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


@pytest.mark.asyncio
async def test_background_ml_service_adapter():
    import uuid
    from unittest.mock import AsyncMock, MagicMock, patch
    from infrastructure.api.routers.profiles import BackgroundMlServiceAdapter

    mock_bg = MagicMock()
    mock_ml = AsyncMock()
    mock_ml.get_candidate_embedding.return_value = [0.1, 0.2]

    adapter = BackgroundMlServiceAdapter(mock_bg, mock_ml)
    vec = await adapter.get_candidate_embedding("hello")
    assert vec == [0.1, 0.2]

    fake_id = uuid.uuid4()
    adapter.schedule_embedding_update(fake_id, "test text")
    mock_bg.add_task.assert_called_once()

    with patch("infrastructure.api.routers.profiles.session_factory") as mock_sf, \
         patch("infrastructure.api.routers.profiles.SqlAlchemyUserRepository") as mock_repo_cls:
        mock_ctx = AsyncMock()
        mock_session = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_session
        mock_sf.return_value = mock_ctx
        mock_repo = AsyncMock()
        mock_repo_cls.return_value = mock_repo

        await adapter._task(fake_id, "test text")
        mock_repo.update_embedding_candidato.assert_called_once_with(fake_id, [0.1, 0.2])
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_candidate_cv_presigned_url_flow():
    import uuid
    from unittest.mock import AsyncMock, patch
    from fastapi import HTTPException
    from domain.entities.candidate_profile import CandidateProfile
    from domain.entities.user import User, UserRole
    from infrastructure.api.routers.profiles import get_candidate_cv_presigned_url

    mock_session = AsyncMock()
    from datetime import datetime
    fake_user = User(id=uuid.uuid4(), email="u@test.com", password_hash="h", role=UserRole.CANDIDATE, created_at=datetime.now())
    fake_profile_id = uuid.uuid4()

    # 1. Profile not found
    with patch("infrastructure.api.routers.profiles.SqlAlchemyUserRepository.get_candidate_profile_by_id", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            await get_candidate_cv_presigned_url(fake_profile_id, current_user=fake_user, session=mock_session)
        assert exc_info.value.status_code == 404
        assert exc_info.value.detail == "Perfil no encontrado"

    # 2. Profile has no cv_file_url
    fake_profile_no_cv = CandidateProfile(
        id=fake_profile_id, user_id=fake_user.id, full_name="Pedro", skills=[], experience_years=1, location=None, education=None, cv_text=None, cv_file_url=None
    )
    with patch("infrastructure.api.routers.profiles.SqlAlchemyUserRepository.get_candidate_profile_by_id", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = fake_profile_no_cv
        with pytest.raises(HTTPException) as exc_info:
            await get_candidate_cv_presigned_url(fake_profile_id, current_user=fake_user, session=mock_session)
        assert exc_info.value.status_code == 404
        assert "no ha subido" in exc_info.value.detail

    # 3. Profile has cv_file_url -> returns presigned url
    fake_profile_with_cv = CandidateProfile(
        id=fake_profile_id, user_id=fake_user.id, full_name="Pedro", skills=[], experience_years=1, location=None, education=None, cv_text="cv", cv_file_url="cvs/pedro.pdf"
    )
    with patch("infrastructure.api.routers.profiles.SqlAlchemyUserRepository.get_candidate_profile_by_id", new_callable=AsyncMock) as mock_get, \
         patch("infrastructure.adapters.storage.s3_file_storage.S3FileStorageAdapter.generate_presigned_url", new_callable=AsyncMock) as mock_gen:
        mock_get.return_value = fake_profile_with_cv
        mock_gen.return_value = "https://presigned.s3.com/cv.pdf"
        res = await get_candidate_cv_presigned_url(fake_profile_id, current_user=fake_user, session=mock_session)
        assert res["profile_id"] == str(fake_profile_id)
        assert res["cv_url"] == "https://presigned.s3.com/cv.pdf"


@pytest.mark.asyncio
async def test_obtener_recomendaciones_fallback():
    import uuid
    from datetime import datetime
    from unittest.mock import AsyncMock, MagicMock, patch
    from domain.entities.user import User, UserRole
    from domain.entities.vacante import Vacante, VacanteEstado
    from infrastructure.api.routers.recomendaciones import obtener_recomendaciones

    mock_request = MagicMock()
    mock_request.headers.get.return_value = "es"
    mock_session = AsyncMock()
    fake_user = User(id=uuid.uuid4(), email="u@test.com", password_hash="h", role=UserRole.CANDIDATE, created_at=datetime.now())

    with patch("application.use_cases.get_recomendaciones.GetRecomendacionesUseCase.execute", side_effect=Exception("ML timeout")), \
         patch("infrastructure.adapters.persistence.vacante_repository.SqlAlchemyVacanteRepository.list_activas", new_callable=AsyncMock) as mock_list:
        fake_vacante = Vacante(
            id=uuid.uuid4(),
            empresa_id=uuid.uuid4(),
            titulo="Dev Fullstack",
            descripcion="Desc",
            requisitos=["Python"],
            ubicacion="Bogota",
            estado=VacanteEstado.ACTIVA,
            creado_en=datetime.now(),
        )
        mock_list.return_value = [fake_vacante]

        res = await obtener_recomendaciones(uuid.uuid4(), request=mock_request, current_user=fake_user, session=mock_session)
        assert len(res) == 1
        assert res[0].titulo == "Dev Fullstack"


@pytest.mark.asyncio
async def test_upload_cv_endpoint_validations_and_success():
    import uuid
    from datetime import datetime
    from unittest.mock import AsyncMock, MagicMock, patch
    from fastapi import HTTPException
    from domain.entities.user import User, UserRole
    from domain.entities.candidate_profile import CandidateProfile
    from infrastructure.api.routers.profiles import upload_cv

    fake_candidate = User(id=uuid.uuid4(), email="c@test.com", password_hash="h", role=UserRole.CANDIDATE, created_at=datetime.now())
    fake_company = User(id=uuid.uuid4(), email="e@test.com", password_hash="h", role=UserRole.COMPANY, created_at=datetime.now())
    fake_profile_id = uuid.uuid4()
    mock_bg = MagicMock()
    mock_session = AsyncMock()
    mock_parser = MagicMock()

    # 1. Non-candidate forbidden
    mock_file = MagicMock()
    mock_file.content_type = "application/pdf"
    with pytest.raises(HTTPException) as exc_info:
        await upload_cv(fake_profile_id, mock_file, mock_bg, current_user=fake_company, cv_parser=mock_parser, session=mock_session)
    assert exc_info.value.status_code == 403

    # 2. Invalid mime type
    mock_file_invalid = MagicMock()
    mock_file_invalid.content_type = "application/x-sh"
    with pytest.raises(HTTPException) as exc_info:
        await upload_cv(fake_profile_id, mock_file_invalid, mock_bg, current_user=fake_candidate, cv_parser=mock_parser, session=mock_session)
    assert exc_info.value.status_code == 415

    # 3. File too large (>5MB)
    mock_file_large = MagicMock()
    mock_file_large.content_type = "application/pdf"
    mock_file_large.read = AsyncMock(return_value=b"A" * (6 * 1024 * 1024))
    with pytest.raises(HTTPException) as exc_info:
        await upload_cv(fake_profile_id, mock_file_large, mock_bg, current_user=fake_candidate, cv_parser=mock_parser, session=mock_session)
    assert exc_info.value.status_code == 413

    # 4. Successful upload with presigned url
    mock_file_ok = MagicMock()
    mock_file_ok.content_type = "application/pdf"
    mock_file_ok.filename = "my_cv.pdf"
    mock_file_ok.read = AsyncMock(return_value=b"%PDF-1.4 test")

    fake_profile = CandidateProfile(
        id=fake_profile_id,
        user_id=fake_candidate.id,
        full_name="Carlos Gomez",
        skills=["Python"],
        experience_years=3,
        location="Bogota",
        education="Ingenieria",
        cv_text="Resumen del CV de Carlos",
        cv_file_url="cvs/carlos.pdf",
    )

    with patch("application.use_cases.upload_cv.UploadCvUseCase.execute", new_callable=AsyncMock) as mock_uc, \
         patch("infrastructure.adapters.storage.s3_file_storage.S3FileStorageAdapter.generate_presigned_url", new_callable=AsyncMock) as mock_url:
        mock_uc.return_value = fake_profile
        mock_url.return_value = "https://s3.aws.com/presigned-cv.pdf"

        res = await upload_cv(fake_profile_id, mock_file_ok, mock_bg, current_user=fake_candidate, cv_parser=mock_parser, session=mock_session)
        assert res.profile_id == fake_profile_id
        assert res.cv_download_url == "https://s3.aws.com/presigned-cv.pdf"
        assert "Carlos" in res.cv_preview




