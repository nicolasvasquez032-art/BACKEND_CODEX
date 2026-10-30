from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, UploadFile, status
from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from application.use_cases.get_candidate_profile import (
    GetCandidateProfileCommand,
    GetCandidateProfileUseCase,
)
from application.use_cases.update_candidate_profile import (
    UpdateCandidateProfileCommand,
    UpdateCandidateProfileUseCase,
)
from application.use_cases.upload_cv import UploadCvCommand, UploadCvUseCase
from domain.entities.user import User, UserRole
from domain.exceptions import CVProcessingError, PermissionDeniedError, ProfileNotFoundError
from infrastructure.adapters.cv_parser.composite_parser import CompositeCvParser
from infrastructure.adapters.ml_client.http_ml_service import HttpMlServiceAdapter
from infrastructure.adapters.persistence.database import get_read_session, get_session, session_factory
from infrastructure.adapters.persistence.user_repository import SqlAlchemyUserRepository
from infrastructure.adapters.storage.s3_file_storage import S3FileStorageAdapter
from infrastructure.api.dependencies import get_current_user, get_cv_parser
from infrastructure.api.schemas.profiles import (
    CVUploadResponse,
    ProfileResponse,
    ProfileUpdateRequest,
)
from infrastructure.config import settings

router = APIRouter(prefix="/perfiles", tags=["perfiles"])


class BackgroundMlServiceAdapter:
    """Delega la generación y almacenamiento de embeddings de IA a BackgroundTasks."""

    def __init__(self, background_tasks: BackgroundTasks, ml_service: HttpMlServiceAdapter):
        self._bg = background_tasks
        self._ml_service = ml_service

    async def get_candidate_embedding(self, text: str) -> list[float]:
        return await self._ml_service.get_candidate_embedding(text)

    def schedule_embedding_update(self, profile_id: UUID, text: str) -> None:
        self._bg.add_task(self._task, profile_id, text)

    async def _task(self, profile_id: UUID, text: str) -> None:
        try:
            vector = await self._ml_service.get_candidate_embedding(text)
            async with session_factory() as session:
                repo = SqlAlchemyUserRepository(session)
                await repo.update_embedding_candidato(profile_id, vector)
                await session.commit()
            logger.info(f"Embedding de IA para perfil {profile_id} generado exitosamente en segundo plano.")
        except Exception as exc:
            logger.error(f"Fallo al generar embedding en segundo plano para {profile_id}: {exc}")


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_read_session),
) -> ProfileResponse:
    """Devuelve el perfil del candidato autenticado (usando su JWT).

    Útil para que el cliente móvil obtenga el profile_id sin conocerlo previamente.
    """
    repo = SqlAlchemyUserRepository(session)
    profile = await repo.get_candidate_profile_by_user_id(current_user.id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado")

    return ProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        full_name=profile.full_name,
        skills=profile.skills,
        experience_years=profile.experience_years,
        location=profile.location,
        education=profile.education,
        cv_text=profile.cv_text,
        phone=profile.phone,
        portfolio_url=profile.portfolio_url,
        about_me=profile.about_me,
        job_title=profile.job_title,
    )


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ProfileResponse:
    """Obtiene el perfil de un candidato.

    - El candidato dueño puede ver su propio perfil.
    - Empresas y administradores pueden ver cualquier perfil.
    """
    repo = SqlAlchemyUserRepository(session)
    use_case = GetCandidateProfileUseCase(repo)

    try:
        profile = await use_case.execute(
            GetCandidateProfileCommand(
                profile_id=profile_id,
                requesting_user_id=current_user.id,
                requesting_user_role=current_user.role.value,
            )
        )
    except ProfileNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado")
    except PermissionDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    return ProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        full_name=profile.full_name,
        skills=profile.skills,
        experience_years=profile.experience_years,
        location=profile.location,
        education=profile.education,
        cv_text=profile.cv_text,
        phone=profile.phone,
        portfolio_url=profile.portfolio_url,
        about_me=profile.about_me,
        job_title=profile.job_title,
    )


@router.put("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: UUID,
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ProfileResponse:
    """Actualiza el perfil del candidato autenticado."""
    if current_user.role != UserRole.CANDIDATE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los candidatos pueden editar perfiles",
        )

    repo = SqlAlchemyUserRepository(session)
    ml_service = HttpMlServiceAdapter(settings.ml_service_url)
    use_case = UpdateCandidateProfileUseCase(repo, ml_service)

    try:
        profile = await use_case.execute(
            UpdateCandidateProfileCommand(
                profile_id=profile_id,
                requesting_user_id=current_user.id,
                full_name=request.full_name,
                skills=request.skills,
                experience_years=request.experience_years,
                location=request.location,
                education=request.education,
                phone=request.phone,
                portfolio_url=request.portfolio_url,
                about_me=request.about_me,
                job_title=request.job_title,
            )
        )
        await session.commit()
    except ProfileNotFoundError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado")
    except PermissionDeniedError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al guardar los cambios",
        ) from exc

    return ProfileResponse(
        id=profile.id,
        user_id=profile.user_id,
        full_name=profile.full_name,
        skills=profile.skills,
        experience_years=profile.experience_years,
        location=profile.location,
        education=profile.education,
        cv_text=profile.cv_text,
        phone=profile.phone,
        portfolio_url=profile.portfolio_url,
        about_me=profile.about_me,
        job_title=profile.job_title,
    )


@router.post("/{profile_id}/cv", response_model=CVUploadResponse, status_code=status.HTTP_200_OK)
async def upload_cv(
    profile_id: UUID,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    cv_parser: CompositeCvParser = Depends(get_cv_parser),
    session: AsyncSession = Depends(get_session),
) -> CVUploadResponse:
    """Sube un CV en formato PDF o imagen (JPG, PNG, WEBP) y extrae su texto.

    La extracción se procesa y el cálculo de embeddings vectoriales de IA se
    delega a una tarea en segundo plano (BackgroundTasks) para responder de inmediato.
    """
    if current_user.role != UserRole.CANDIDATE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los candidatos pueden subir su CV",
        )

    # 🛡️ VALIDACIÓN DE SEGURIDAD OWASP (MIME Type)
    ALLOWED_MIMES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
    if file.content_type not in ALLOWED_MIMES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Formato de archivo peligroso o no permitido: {file.content_type}. Solo se aceptan PDF o Imágenes.",
        )

    file_bytes = await file.read()
    
    # 🛡️ PREVENCIÓN DoS (Límite de tamaño: 5MB)
    if len(file_bytes) > 5 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="El archivo excede el límite de 5MB.",
        )

    mime_type = file.content_type
    
    storage = S3FileStorageAdapter()
    repo = SqlAlchemyUserRepository(session)
    ml_adapter = BackgroundMlServiceAdapter(
        background_tasks, HttpMlServiceAdapter(settings.ml_service_url)
    )
    use_case = UploadCvUseCase(repo, cv_parser, ml_adapter, storage=storage)

    try:
        profile = await use_case.execute(
            UploadCvCommand(
                profile_id=profile_id,
                requesting_user_id=current_user.id,
                file_bytes=file_bytes,
                mime_type=mime_type,
                file_name=file.filename or "curriculum.pdf",
            )
        )
        await session.commit()
    except ProfileNotFoundError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado")
    except PermissionDeniedError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    except CVProcessingError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al guardar el CV",
        ) from exc

    download_url = None
    if profile.cv_file_url:
        try:
            download_url = await storage.generate_presigned_url(
                profile.cv_file_url,
                expires_in_seconds=settings.s3_presigned_url_expire_seconds,
            )
        except Exception as e:
            logger.warning(f"No se pudo generar presigned url inmediata: {e}")

    cv_preview = (profile.cv_text or "")[:200]
    return CVUploadResponse(
        profile_id=profile.id,
        message="CV procesado y guardado exitosamente",
        cv_preview=cv_preview,
        cv_download_url=download_url,
    )


@router.get("/{profile_id}/cv-url")
async def get_candidate_cv_presigned_url(
    profile_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_read_session),
) -> dict[str, str | int]:
    """Genera una URL temporal prefirmada (Presigned URL) de AWS S3 válida por 15 minutos.

    Permite a empresas o al propio candidato descargar/visualizar el archivo original con seguridad.
    """
    repo = SqlAlchemyUserRepository(session)
    profile = await repo.get_candidate_profile_by_id(profile_id)
    if profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil no encontrado")

    if not profile.cv_file_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El candidato aún no ha subido un archivo original de CV.",
        )

    storage = S3FileStorageAdapter()
    presigned_url = await storage.generate_presigned_url(
        profile.cv_file_url,
        expires_in_seconds=settings.s3_presigned_url_expire_seconds,
    )
    return {
        "profile_id": str(profile_id),
        "cv_url": presigned_url,
        "expires_in_seconds": settings.s3_presigned_url_expire_seconds,
    }
