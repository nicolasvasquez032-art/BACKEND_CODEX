from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from application.use_cases.cambiar_estado_postulacion import (
    CambiarEstadoPostulacionCommand,
    CambiarEstadoPostulacionUseCase,
)
from application.use_cases.listar_postulaciones import (
    ListarPostulacionesCandidatoQuery,
    ListarPostulacionesCandidatoUseCase,
    ListarPostulacionesVacanteQuery,
    ListarPostulacionesVacanteUseCase,
)
from application.use_cases.postularse_a_vacante import (
    PostularseAVacanteCommand,
    PostularseAVacanteUseCase,
)
from domain.entities.user import User
from domain.exceptions import (
    DuplicatePostulacionError,
    InvalidEstadoTransitionError,
    PermissionDeniedError,
    PostulacionNotFoundError,
    VacanteNotFoundError,
)
from infrastructure.adapters.persistence.database import get_session
from infrastructure.adapters.persistence.postulacion_repository import (
    SqlAlchemyPostulacionRepository,
)
from infrastructure.adapters.persistence.vacante_repository import SqlAlchemyVacanteRepository
from infrastructure.api.dependencies import get_current_user
from infrastructure.api.schemas.postulaciones import (
    CambiarEstadoPostulacionRequest,
    PostulacionResponse,
    PostularseRequest,
)

router = APIRouter(prefix="/postulaciones", tags=["postulaciones"])


def _to_response(p) -> PostulacionResponse:
    return PostulacionResponse(
        id=p.id,
        candidato_id=p.candidato_id,
        vacante_id=p.vacante_id,
        estado=p.estado,
        fecha=p.fecha,
        score_match=p.score_match,
    )


@router.post("", response_model=PostulacionResponse, status_code=status.HTTP_201_CREATED)
async def postularse(
    request: PostularseRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PostulacionResponse:
    """Postula un candidato a una vacante activa (RF-03.1 y RF-03.2)."""
    postulaciones_repo = SqlAlchemyPostulacionRepository(session)
    vacantes_repo = SqlAlchemyVacanteRepository(session)
    use_case = PostularseAVacanteUseCase(postulaciones_repo, vacantes_repo)

    try:
        postulacion = await use_case.execute(
            PostularseAVacanteCommand(
                candidato_id=request.candidato_id,
                vacante_id=request.vacante_id,
            )
        )
        await session.commit()
    except VacanteNotFoundError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except DuplicatePostulacionError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una postulación para esta vacante",
        )
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ya existe una postulación para esta vacante",
        )
    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al guardar la postulación",
        ) from exc

    return _to_response(postulacion)


@router.get("/candidato/{candidato_id}", response_model=list[PostulacionResponse])
async def listar_postulaciones_candidato(
    candidato_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[PostulacionResponse]:
    """Retorna el historial de postulaciones de un candidato (RF-03.4)."""
    repo = SqlAlchemyPostulacionRepository(session)
    use_case = ListarPostulacionesCandidatoUseCase(repo)

    try:
        postulaciones = await use_case.execute(
            ListarPostulacionesCandidatoQuery(
                candidato_id=candidato_id,
                requesting_user_id=current_user.id,
                requesting_user_role=current_user.role.value,
            )
        )
    except PermissionDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    return [_to_response(p) for p in postulaciones]


@router.get("/vacante/{vacante_id}", response_model=list[PostulacionResponse])
async def listar_postulaciones_vacante(
    vacante_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[PostulacionResponse]:
    """Retorna las postulaciones de una vacante para el kanban de la empresa (RF-03.3)."""
    postulaciones_repo = SqlAlchemyPostulacionRepository(session)
    vacantes_repo = SqlAlchemyVacanteRepository(session)
    use_case = ListarPostulacionesVacanteUseCase(postulaciones_repo, vacantes_repo)

    try:
        postulaciones = await use_case.execute(
            ListarPostulacionesVacanteQuery(
                vacante_id=vacante_id,
                requesting_empresa_id=current_user.id,
            )
        )
    except VacanteNotFoundError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacante no encontrada")
    except PermissionDeniedError:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    return [_to_response(p) for p in postulaciones]


@router.patch("/{postulacion_id}/estado", response_model=PostulacionResponse)
async def cambiar_estado_postulacion(
    postulacion_id: UUID,
    request: CambiarEstadoPostulacionRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PostulacionResponse:
    """Avanza el estado de una postulación en el kanban (RF-03.3)."""
    postulaciones_repo = SqlAlchemyPostulacionRepository(session)
    vacantes_repo = SqlAlchemyVacanteRepository(session)
    use_case = CambiarEstadoPostulacionUseCase(postulaciones_repo, vacantes_repo)

    try:
        postulacion = await use_case.execute(
            CambiarEstadoPostulacionCommand(
                postulacion_id=postulacion_id,
                requesting_empresa_id=current_user.id,
                nuevo_estado=request.estado,
            )
        )
        await session.commit()
    except PostulacionNotFoundError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Postulación no encontrada"
        )
    except VacanteNotFoundError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacante no encontrada")
    except PermissionDeniedError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    except InvalidEstadoTransitionError as exc:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))
    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar el estado",
        ) from exc

    return _to_response(postulacion)
