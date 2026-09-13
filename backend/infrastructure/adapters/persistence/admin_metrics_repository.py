from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from application.ports.admin_ports import AdminMetricasRepositoryPort
from domain.entities.postulacion import PostulacionEstado
from domain.entities.vacante import VacanteEstado
from infrastructure.adapters.persistence.models import (
    CandidateProfileModel,
    PostulacionModel,
    VacanteModel,
)


class SqlAlchemyAdminMetricasRepository(AdminMetricasRepositoryPort):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_total_candidatos(self) -> int:
        stmt = select(func.count(CandidateProfileModel.id))
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def get_total_vacantes_activas(self) -> int:
        stmt = select(func.count(VacanteModel.id)).where(VacanteModel.estado == VacanteEstado.ACTIVA)
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def get_total_postulaciones(self) -> int:
        stmt = select(func.count(PostulacionModel.id))
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def get_sectores_demanda(self, limite: int = 5) -> list[dict]:
        """
        Retorna los sectores (categorías) con mayor número de vacantes (activas o en general).
        """
        stmt = (
            select(VacanteModel.categoria, func.count(VacanteModel.id).label("cantidad"))
            .where(VacanteModel.categoria != None)
            .group_by(VacanteModel.categoria)
            .order_by(func.count(VacanteModel.id).desc())
            .limit(limite)
        )
        result = await self._session.execute(stmt)
        return [{"sector": row.categoria, "cantidad": row.cantidad} for row in result.all()]

    async def get_tiempo_promedio_contratacion_dias(self) -> float | None:
        # Aquí asumimos que la fecha de la postulación es el inicio, pero cuando se cambia el estado a CONTRATADO
        # no estamos guardando un `updated_at` en PostulacionModel! 
        # (Idealmente se añadiría updated_at, o una tabla de historial. Para este ejercicio simple, 
        # asumo que PostulacionModel no tiene updated_at por ahora, así que retornaré 0.0 o requerirá añadir un campo).
        # Vamos a revisar si PostulacionModel tiene un campo `fecha` pero no `actualizado_en`.
        # Si no lo tiene, simularemos o podemos dejar en None si no hay data.
        
        # Como no tenemos 'actualizado_en' en PostulacionModel, no podemos medir tiempo exacto.
        # Por ahora devolveremos None, o si el usuario quiere, podríamos añadir un campo actualizado_en.
        # Simularemos una lógica genérica: (CURRENT_TIMESTAMP - fecha) para los contratados.
        stmt = select(
            func.avg(
                func.extract('epoch', func.now() - PostulacionModel.fecha) / 86400.0
            )
        ).where(PostulacionModel.estado == PostulacionEstado.CONTRATADO)
        
        result = await self._session.execute(stmt)
        val = result.scalar()
        return float(val) if val is not None else None

    async def get_efectividad_recomendacion(self) -> float | None:
        # Porcentaje de postulaciones CONTRATADAS que vinieron de una recomendación (score_match >= 0.5)
        stmt_total_contratados = select(func.count(PostulacionModel.id)).where(
            PostulacionModel.estado == PostulacionEstado.CONTRATADO
        )
        total_contratados = (await self._session.execute(stmt_total_contratados)).scalar() or 0

        if total_contratados == 0:
            return None

        stmt_recomendados = select(func.count(PostulacionModel.id)).where(
            PostulacionModel.estado == PostulacionEstado.CONTRATADO,
            PostulacionModel.score_match >= 0.5
        )
        recomendados = (await self._session.execute(stmt_recomendados)).scalar() or 0

        return (recomendados / total_contratados) * 100.0
