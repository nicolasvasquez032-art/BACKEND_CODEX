from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from application.ports.ml_service_port import RecomendacionDTO
from application.services.i18n_service import I18nService
from application.use_cases.get_recomendaciones import GetRecomendacionesUseCase
from domain.entities.user import User, UserRole
from infrastructure.adapters.ml_client.http_ml_service import HttpMlServiceAdapter
from infrastructure.adapters.persistence.database import get_read_session
from infrastructure.adapters.persistence.vacante_repository import SqlAlchemyVacanteRepository
from infrastructure.api.dependencies import get_current_user, require_role
from infrastructure.config import settings

router = APIRouter(prefix="/recomendaciones", tags=["recomendaciones"])


class RecomendacionResponse(BaseModel):
    vacante_id: UUID
    titulo: str
    empresa_id: UUID
    score_similitud: float
    explicacion: str


@router.get("/candidato/{candidato_id}", response_model=list[RecomendacionResponse])
async def obtener_recomendaciones(
    candidato_id: UUID,
    request: Request,
    current_user: User = Depends(require_role(UserRole.CANDIDATE)),
    session: AsyncSession = Depends(get_read_session),
) -> list[RecomendacionResponse]:
    """Obtiene vacantes recomendadas para un candidato (RF-04). Soporta I18n y fallback resiliente."""
        
    ml_adapter = HttpMlServiceAdapter(settings.ml_service_url)
    use_case = GetRecomendacionesUseCase(ml_adapter)
    lang = request.headers.get("accept-language")
    
    try:
        recomendaciones = await use_case.execute(candidato_id)
    except Exception as e:
        logger.warning(
            f"Microservicio ML no disponible o en timeout ({e}). "
            f"Activando fallback resiliente a vacantes activas destacadas."
        )
        vacantes_repo = SqlAlchemyVacanteRepository(session)
        activas = await vacantes_repo.list_activas(limit=10)
        recomendaciones = [
            RecomendacionDTO(
                vacante_id=v.id,
                titulo=v.titulo,
                empresa_id=v.empresa_id,
                score_similitud=0.75,
                explicacion="Vacante destacada recomendada para tu perfil profesional.",
            )
            for v in activas
        ]

    return [
        RecomendacionResponse(
            vacante_id=r.vacante_id,
            titulo=I18nService.translate_title(r.titulo, lang),
            empresa_id=r.empresa_id,
            score_similitud=r.score_similitud,
            explicacion=I18nService.translate_recommendation_explanation(r.explicacion, lang)
        )
        for r in recomendaciones
    ]
