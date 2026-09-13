from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
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
from infrastructure.adapters.persistence.database import get_session
from infrastructure.adapters.persistence.user_repository import SqlAlchemyUserRepository
from infrastructure.adapters.ml_client.http_ml_service import HttpMlServiceAdapter
from infrastructure.api.dependencies import get_current_user, get_cv_parser
from infrastructure.config import settings
from infrastructure.api.schemas.profiles import CVUploadResponse, ProfileResponse, ProfileUpdateRequest

router = APIRouter(prefix="/perfiles", tags=["perfiles"])


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
    )


@router.post("/{profile_id}/cv", response_model=CVUploadResponse, status_code=status.HTTP_200_OK)
async def upload_cv(
    profile_id: UUID,
    file: UploadFile,
    current_user: User = Depends(get_current_user),
    cv_parser: CompositeCvParser = Depends(get_cv_parser),
    session: AsyncSession = Depends(get_session),
) -> CVUploadResponse:
    """Sube un CV en formato PDF o imagen (JPG, PNG, WEBP) y extrae su texto.

    El texto extraído se guarda en el perfil del candidato para generar
    el embedding semántico en el Sprint 3.
    """
    if current_user.role != UserRole.CANDIDATE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los candidatos pueden subir su CV",
        )

    file_bytes = await file.read()
    mime_type = file.content_type or "application/octet-stream"

    repo = SqlAlchemyUserRepository(session)
    ml_service = HttpMlServiceAdapter(settings.ml_service_url)
    use_case = UploadCvUseCase(repo, cv_parser, ml_service)

    try:
        profile = await use_case.execute(
            UploadCvCommand(
                profile_id=profile_id,
                requesting_user_id=current_user.id,
                file_bytes=file_bytes,
                mime_type=mime_type,
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

    cv_preview = (profile.cv_text or "")[:200]
    return CVUploadResponse(
        profile_id=profile.id,
        message="CV procesado y guardado exitosamente",
        cv_preview=cv_preview,
    )
