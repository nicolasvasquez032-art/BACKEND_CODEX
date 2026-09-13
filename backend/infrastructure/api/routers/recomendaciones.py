from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from application.use_cases.get_recomendaciones import GetRecomendacionesUseCase
from domain.entities.user import User, UserRole
from infrastructure.adapters.ml_client.http_ml_service import HttpMlServiceAdapter
from infrastructure.api.dependencies import get_current_user
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
    current_user: User = Depends(get_current_user),
) -> list[RecomendacionResponse]:
    """Obtiene vacantes recomendadas para un candidato (RF-04)."""
    
    # Solo el propio candidato puede ver sus recomendaciones
    if current_user.role != UserRole.CANDIDATE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los candidatos pueden recibir recomendaciones"
        )
        
    ml_adapter = HttpMlServiceAdapter(settings.ml_service_url)
    use_case = GetRecomendacionesUseCase(ml_adapter)
    
    try:
        recomendaciones = await use_case.execute(candidato_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo recomendaciones: {str(e)}"
        )

    return [
        RecomendacionResponse(
            vacante_id=r.vacante_id,
            titulo=r.titulo,
            empresa_id=r.empresa_id,
            score_similitud=r.score_similitud,
            explicacion=r.explicacion
        )
        for r in recomendaciones
    ]
