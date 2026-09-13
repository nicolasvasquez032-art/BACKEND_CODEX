from typing import Protocol


class AdminMetricasRepositoryPort(Protocol):
    async def get_total_candidatos(self) -> int:
        pass

    async def get_total_vacantes_activas(self) -> int:
        pass

    async def get_total_postulaciones(self) -> int:
        pass

    async def get_sectores_demanda(self, limite: int = 5) -> list[dict]:
        """Retorna una lista de diccionarios con {'sector': str, 'cantidad': int}."""
        pass

    async def get_tiempo_promedio_contratacion_dias(self) -> float | None:
        """Retorna el tiempo promedio en días desde la creación de la postulación hasta el estado CONTRATADO."""
        pass

    async def get_efectividad_recomendacion(self) -> float | None:
        """Retorna el porcentaje de postulaciones CONTRATADAS que provinieron de un match (score_match >= 0.5)."""
        pass
