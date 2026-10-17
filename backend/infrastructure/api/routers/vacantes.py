from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from application.services.i18n_service import I18nService
from application.use_cases.actualizar_vacante import (
    ActualizarVacanteCommand,
    ActualizarVacanteUseCase,
)
from application.use_cases.cambiar_estado_vacante import (
    CambiarEstadoVacanteCommand,
    CambiarEstadoVacanteUseCase,
)
from application.use_cases.eliminar_vacante import EliminarVacanteCommand, EliminarVacanteUseCase
from application.use_cases.listar_vacantes import ListarVacantesQuery, ListarVacantesUseCase
from application.use_cases.publicar_vacante import PublicarVacanteCommand, PublicarVacanteUseCase
from domain.entities.user import User, UserRole
from domain.exceptions import PermissionDeniedError, VacanteNotFoundError
from infrastructure.adapters.cache.redis_cache_service import RedisCacheService
from infrastructure.adapters.fcm_adapter import RealFcmAdapter
from infrastructure.adapters.ml_client.http_ml_service import HttpMlServiceAdapter
from infrastructure.adapters.persistence.database import get_read_session, get_session
from infrastructure.adapters.persistence.notificacion_repository import (
    SqlAlchemyNotificacionRepository,
)
from infrastructure.adapters.persistence.vacante_repository import SqlAlchemyVacanteRepository
from infrastructure.api.dependencies import get_current_user, require_role
from infrastructure.api.schemas.vacantes import (
    ActualizarVacanteRequest,
    CambiarEstadoVacanteRequest,
    PublicarVacanteRequest,
    VacanteResponse,
)
from infrastructure.config import settings

router = APIRouter(prefix="/vacantes", tags=["vacantes"])


def _to_response(vacante, lang: str | None = None) -> VacanteResponse:
    localized = I18nService.translate_vacante_fields(
        titulo=vacante.titulo,
        descripcion=vacante.descripcion,
        requisitos=vacante.requisitos or [],
        ubicacion=vacante.ubicacion,
        categoria=vacante.categoria,
        lang=lang,
    )
    return VacanteResponse(
        id=vacante.id,
        empresa_id=vacante.empresa_id,
        titulo=localized["titulo"],
        descripcion=localized["descripcion"],
        requisitos=localized["requisitos"],
        ubicacion=localized["ubicacion"],
        estado=vacante.estado,
        categoria=localized["categoria"],
        salario_min=vacante.salario_min,
        salario_max=vacante.salario_max,
        latitud=vacante.latitud,
        longitud=vacante.longitud,
        creado_en=vacante.creado_en,
    )


@router.get("", response_model=list[VacanteResponse])
async def listar_vacantes(
    request: Request,
    ubicacion: str | None = Query(default=None, max_length=180),
    categoria: str | None = Query(default=None, max_length=100),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_read_session),
) -> list[VacanteResponse]:
    """Lista vacantes activas con aceleración por caché Redis y soporte i18n."""
    lang = request.headers.get("accept-language")
    cache = RedisCacheService.get_instance()
    
    # 1. Consultar en Caché distribuido Redis (O(1) in-memory)
    version = await cache.get_vacantes_version()
    cache_key = f"cache:vacantes:v{version}:{ubicacion}:{categoria}:{offset}:{limit}:{lang}"
    cached_data = await cache.get_json(cache_key)
    if cached_data is not None:
        return [VacanteResponse(**item) for item in cached_data]

    # 2. Cache Miss: Consultar en PostgreSQL
    repo = SqlAlchemyVacanteRepository(session)
    use_case = ListarVacantesUseCase(repo)
    vacantes = await use_case.execute(
        ListarVacantesQuery(ubicacion=ubicacion, categoria=categoria, offset=offset, limit=limit)
    )
    result = [_to_response(v, lang=lang) for v in vacantes]

    # 3. Guardar en Redis de forma asíncrona con TTL de 60 segundos
    await cache.set_json(cache_key, [item.model_dump(mode="json") for item in result], ttl=60)
    return result


@router.get("/{vacante_id}", response_model=VacanteResponse)
async def obtener_vacante(
    vacante_id: UUID,
    request: Request,
    session: AsyncSession = Depends(get_read_session),
) -> VacanteResponse:
    """Obtiene el detalle de una vacante por ID. Soporta traducción vía Accept-Language."""
    repo = SqlAlchemyVacanteRepository(session)
    vacante = await repo.find_by_id(vacante_id)
    lang = request.headers.get("accept-language")
    if not vacante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=I18nService.translate_error("Vacante no encontrada", lang=lang),
        )
    return _to_response(vacante, lang=lang)


@router.post("", response_model=VacanteResponse, status_code=status.HTTP_201_CREATED)
async def publicar_vacante(
    request: PublicarVacanteRequest,
    http_request: Request,
    current_user: User = Depends(require_role(UserRole.COMPANY)),
    session: AsyncSession = Depends(get_session),
) -> VacanteResponse:
    """Publica una nueva vacante. Solo para empresas."""

    repo = SqlAlchemyVacanteRepository(session)
    ml_service = HttpMlServiceAdapter(settings.ml_service_url)
    notificacion_repo = SqlAlchemyNotificacionRepository(session)
    push_port = RealFcmAdapter()
    lang = http_request.headers.get("accept-language")
    
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
        await RedisCacheService.get_instance().invalidate_vacantes_cache()
    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=I18nService.translate_error("Error al guardar la vacante", lang=lang),
        ) from exc

    return _to_response(vacante, lang=lang)


@router.put("/{vacante_id}", response_model=VacanteResponse)
async def actualizar_vacante(
    vacante_id: UUID,
    request: ActualizarVacanteRequest,
    http_request: Request,
    current_user: User = Depends(require_role(UserRole.COMPANY)),
    session: AsyncSession = Depends(get_session),
) -> VacanteResponse:
    """Actualiza los datos de una vacante. Solo la empresa dueña."""
    repo = SqlAlchemyVacanteRepository(session)
    ml_service = HttpMlServiceAdapter(settings.ml_service_url)
    use_case = ActualizarVacanteUseCase(repo, ml_service)
    lang = http_request.headers.get("accept-language")

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
        await RedisCacheService.get_instance().invalidate_vacantes_cache()
    except VacanteNotFoundError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=I18nService.translate_error("Vacante no encontrada", lang=lang),
        )
    except PermissionDeniedError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=I18nService.translate_error("Acceso denegado", lang=lang),
        )
    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=I18nService.translate_error("Error al actualizar la vacante", lang=lang),
        ) from exc

    return _to_response(vacante, lang=lang)


@router.patch("/{vacante_id}/estado", response_model=VacanteResponse)
async def cambiar_estado_vacante(
    vacante_id: UUID,
    request: CambiarEstadoVacanteRequest,
    http_request: Request,
    current_user: User = Depends(require_role(UserRole.COMPANY)),
    session: AsyncSession = Depends(get_session),
) -> VacanteResponse:
    """Cambia el estado de una vacante (activa/pausada/cerrada). Solo la empresa dueña."""
    repo = SqlAlchemyVacanteRepository(session)
    use_case = CambiarEstadoVacanteUseCase(repo)
    lang = http_request.headers.get("accept-language")

    try:
        vacante = await use_case.execute(
            CambiarEstadoVacanteCommand(
                vacante_id=vacante_id,
                requesting_empresa_id=current_user.id,
                nuevo_estado=request.estado,
            )
        )
        await session.commit()
        await RedisCacheService.get_instance().invalidate_vacantes_cache()
    except VacanteNotFoundError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=I18nService.translate_error("Vacante no encontrada", lang=lang),
        )
    except PermissionDeniedError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=I18nService.translate_error("Acceso denegado", lang=lang),
        )
    except SQLAlchemyError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=I18nService.translate_error("Error al cambiar el estado", lang=lang),
        ) from exc

    return _to_response(vacante, lang=lang)


@router.delete("/{vacante_id}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_vacante(
    vacante_id: UUID,
    current_user: User = Depends(require_role(UserRole.COMPANY)),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Elimina una vacante. Solo la empresa dueña."""
    repo = SqlAlchemyVacanteRepository(session)
    use_case = EliminarVacanteUseCase(repo)

    try:
        await use_case.execute(EliminarVacanteCommand(vacante_id, current_user.id))
        await session.commit()
        await RedisCacheService.get_instance().invalidate_vacantes_cache()
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
            detail="Error al eliminar la vacante",
        ) from exc
