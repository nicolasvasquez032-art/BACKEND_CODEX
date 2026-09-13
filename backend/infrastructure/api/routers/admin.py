from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from application.use_cases.get_admin_metrics import (
    GetEfectividadRecomendacionUseCase,
    GetMetricasResumenUseCase,
    GetSectoresDemandaUseCase,
    GetTiempoContratacionUseCase,
    MetricasResumenResponse,
)
from application.use_cases.moderar_vacante import ModerarVacanteUseCase
from domain.entities.user import User, UserRole
from domain.entities.vacante import VacanteEstado
from infrastructure.adapters.persistence.admin_metrics_repository import (
    SqlAlchemyAdminMetricasRepository,
)
from infrastructure.adapters.persistence.database import get_session
from infrastructure.adapters.persistence.vacante_repository import (
    SqlAlchemyVacanteRepository,
)
from infrastructure.api.dependencies import get_current_user, require_role
from infrastructure.api.schemas.vacantes import VacanteResponse

router = APIRouter(
    prefix="/admin", 
    tags=["admin"], 
    dependencies=[Depends(require_role(UserRole.ADMIN))]
)


@router.get("/metricas/resumen", response_model=dict[str, int])
async def get_resumen(
    session: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    repo = SqlAlchemyAdminMetricasRepository(session)
    use_case = GetMetricasResumenUseCase(repo)
    res = await use_case.execute()
    return {
        "total_candidatos": res.total_candidatos,
        "total_vacantes_activas": res.total_vacantes_activas,
        "total_postulaciones": res.total_postulaciones,
    }


@router.get("/metricas/sectores-demanda", response_model=list[dict[str, Any]])
async def get_sectores_demanda(
    limite: int = 5,
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    repo = SqlAlchemyAdminMetricasRepository(session)
    use_case = GetSectoresDemandaUseCase(repo)
    return await use_case.execute(limite)


@router.get("/metricas/tiempo-contratacion", response_model=dict[str, float | None])
async def get_tiempo_contratacion(
    session: AsyncSession = Depends(get_session),
) -> dict[str, float | None]:
    repo = SqlAlchemyAdminMetricasRepository(session)
    use_case = GetTiempoContratacionUseCase(repo)
    tiempo = await use_case.execute()
    return {"tiempo_promedio_dias": tiempo}


@router.get("/metricas/efectividad-recomendacion", response_model=dict[str, float | None])
async def get_efectividad_recomendacion(
    session: AsyncSession = Depends(get_session),
) -> dict[str, float | None]:
    repo = SqlAlchemyAdminMetricasRepository(session)
    use_case = GetEfectividadRecomendacionUseCase(repo)
    porcentaje = await use_case.execute()
    return {"efectividad_porcentaje": porcentaje}


class ModerarVacanteRequest(BaseModel):
    estado: VacanteEstado


@router.patch("/vacantes/{vacante_id}/estado", response_model=VacanteResponse)
async def moderar_vacante(
    vacante_id: UUID,
    request: ModerarVacanteRequest,
    session: AsyncSession = Depends(get_session),
) -> Any:
    vacantes_repo = SqlAlchemyVacanteRepository(session)
    use_case = ModerarVacanteUseCase(vacantes_repo)
    
    try:
        vacante = await use_case.execute(vacante_id, request.estado)
        await session.commit()
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
    return {
        "id": vacante.id,
        "empresa_id": vacante.empresa_id,
        "titulo": vacante.titulo,
        "descripcion": vacante.descripcion,
        "requisitos": vacante.requisitos,
        "ubicacion": vacante.ubicacion,
        "categoria": vacante.categoria,
        "estado": vacante.estado,
        "salario_min": vacante.salario_min,
        "salario_max": vacante.salario_max,
        "latitud": vacante.latitud,
        "longitud": vacante.longitud,
        "creado_en": vacante.creado_en,
    }
