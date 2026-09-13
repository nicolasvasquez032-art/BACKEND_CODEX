from dataclasses import dataclass

from application.ports.admin_ports import AdminMetricasRepositoryPort


@dataclass
class MetricasResumenResponse:
    total_candidatos: int
    total_vacantes_activas: int
    total_postulaciones: int


class GetMetricasResumenUseCase:
    def __init__(self, metrics_repo: AdminMetricasRepositoryPort):
        self._metrics_repo = metrics_repo

    async def execute(self) -> MetricasResumenResponse:
        return MetricasResumenResponse(
            total_candidatos=await self._metrics_repo.get_total_candidatos(),
            total_vacantes_activas=await self._metrics_repo.get_total_vacantes_activas(),
            total_postulaciones=await self._metrics_repo.get_total_postulaciones(),
        )


class GetSectoresDemandaUseCase:
    def __init__(self, metrics_repo: AdminMetricasRepositoryPort):
        self._metrics_repo = metrics_repo

    async def execute(self, limite: int = 5) -> list[dict]:
        return await self._metrics_repo.get_sectores_demanda(limite)


class GetTiempoContratacionUseCase:
    def __init__(self, metrics_repo: AdminMetricasRepositoryPort):
        self._metrics_repo = metrics_repo

    async def execute(self) -> float | None:
        return await self._metrics_repo.get_tiempo_promedio_contratacion_dias()


class GetEfectividadRecomendacionUseCase:
    def __init__(self, metrics_repo: AdminMetricasRepositoryPort):
        self._metrics_repo = metrics_repo

    async def execute(self) -> float | None:
        return await self._metrics_repo.get_efectividad_recomendacion()
