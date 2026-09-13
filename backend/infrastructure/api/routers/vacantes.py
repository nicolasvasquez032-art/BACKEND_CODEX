from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from application.use_cases.actualizar_vacante import (
    ActualizarVacanteCommand,
    ActualizarVacanteUseCase,
)
from application.use_cases.cambiar_estado_vacante import (
    CambiarEstadoVacanteCommand,
    CambiarEstadoVacanteUseCase,
)
from application.use_cases.listar_vacantes import ListarVacantesQuery, ListarVacantesUseCase
from application.use_cases.publicar_vacante import PublicarVacanteUseCase, PublicarVacanteCommand
from domain.entities.user import User, UserRole
from domain.exceptions import PermissionDeniedError, VacanteNotFoundError
from infrastructure.adapters.fcm_adapter import MockFcmAdapter
from infrastructure.adapters.ml_client.http_ml_service import HttpMlServiceAdapter
from infrastructure.adapters.persistence.database import get_session
from infrastructure.adapters.persistence.notificacion_repository import SqlAlchemyNotificacionRepository
from infrastructure.adapters.persistence.vacante_repository import SqlAlchemyVacanteRepository
from infrastructure.api.dependencies import get_current_user
from infrastructure.config import settings
from infrastructure.api.schemas.vacantes import (
    ActualizarVacanteRequest,
    CambiarEstadoVacanteRequest,
    PublicarVacanteRequest,
    VacanteResponse,
)

router = APIRouter(prefix="/vacantes", tags=["vacantes"])


def _to_response(vacante) -> VacanteResponse:
    return VacanteResponse(
        id=vacante.id,
        empresa_id=vacante.empresa_id,
        titulo=vacante.titulo,
        descripcion=vacante.descripcion,
        requisitos=vacante.requisitos,
        ubicacion=vacante.ubicacion,
        estado=vacante.estado,
        categoria=vacante.categoria,
        salario_min=vacante.salario_min,
        salario_max=vacante.salario_max,
        latitud=vacante.latitud,
        longitud=vacante.longitud,
        creado_en=vacante.creado_en,
    )


@router.get("", response_model=list[VacanteResponse])
async def listar_vacantes(
    ubicacion: str | None = Query(default=None, max_length=180),
    categoria: str | None = Query(default=None, max_length=100),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> list[VacanteResponse]:
    """Lista vacantes activas. Endpoint público (no requiere autenticación)."""
    repo = SqlAlchemyVacanteRepository(session)
    use_case = ListarVacantesUseCase(repo)
    vacantes = await use_case.execute(
        ListarVacantesQuery(ubicacion=ubicacion, categoria=categoria, offset=offset, limit=limit)
    )
    return [_to_response(v) for v in vacantes]


@router.post("", response_model=VacanteResponse, status_code=status.HTTP_201_CREATED)
async def publicar_vacante(
    request: PublicarVacanteRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> VacanteResponse:
    """Publica una nueva vacante. Solo para empresas."""
    if current_user.role != UserRole.COMPANY:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo las empresas pueden publicar vacantes",
        )

    repo = SqlAlchemyVacanteRepository(session)
    ml_service = HttpMlServiceAdapter(settings.ml_service_url)
    notificacion_repo = SqlAlchemyNotificacionRepository(session)
    push_port = MockFcmAdapter()
    
    use_case = PublicarVacanteUseCase(repo, ml_service, notificacion_repo, push_port)

    try:
        vacante = await use_case.execute(
            PublicarVacanteCommand(
                empresa_id=current_user.id,
                titulo=request.titulo,
                descripcion=request.descripcion,
                requisitos=request.requisitos,
                ubicacion=request.ubicacion,
                categoria=request.categoria,
                salario_min=request.salario_min,
                salario_max=request.salario_max,
                latitud=request.latitud,
                longitud=request.longitud,
            )
        )
        await session.commit()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al guardar la vacante",
        ) from exc

    return _to_response(vacante)


@router.put("/{vacante_id}", response_model=VacanteResponse)
async def actualizar_vacante(
    vacante_id: UUID,
    request: ActualizarVacanteRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> VacanteResponse:
    """Actualiza los datos de una vacante. Solo la empresa dueña."""
    repo = SqlAlchemyVacanteRepository(session)
    ml_service = HttpMlServiceAdapter(settings.ml_service_url)
    use_case = ActualizarVacanteUseCase(repo, ml_service)

    try:
        vacante = await use_case.execute(
            ActualizarVacanteCommand(
                vacante_id=vacante_id,
                requesting_empresa_id=current_user.id,
                titulo=request.titulo,
                descripcion=request.descripcion,
                requisitos=request.requisitos,
                ubicacion=request.ubicacion,
                categoria=request.categoria,
                salario_min=request.salario_min,
                salario_max=request.salario_max,
            )
        )
        await session.commit()
    except VacanteNotFoundError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacante no encontrada")
    except PermissionDeniedError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al actualizar la vacante",
        ) from exc

    return _to_response(vacante)


@router.patch("/{vacante_id}/estado", response_model=VacanteResponse)
async def cambiar_estado_vacante(
    vacante_id: UUID,
    request: CambiarEstadoVacanteRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> VacanteResponse:
    """Cambia el estado de una vacante (activa/pausada/cerrada). Solo la empresa dueña."""
    repo = SqlAlchemyVacanteRepository(session)
    use_case = CambiarEstadoVacanteUseCase(repo)

    try:
        vacante = await use_case.execute(
            CambiarEstadoVacanteCommand(
                vacante_id=vacante_id,
                requesting_empresa_id=current_user.id,
                nuevo_estado=request.estado,
            )
        )
        await session.commit()
    except VacanteNotFoundError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacante no encontrada")
    except PermissionDeniedError:
        await session.rollback()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al cambiar el estado",
        ) from exc

    return _to_response(vacante)
