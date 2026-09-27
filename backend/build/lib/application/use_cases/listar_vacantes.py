from dataclasses import dataclass

from application.ports.vacante_repository import VacanteRepositoryPort
from domain.entities.vacante import Vacante


@dataclass(frozen=True)
class ListarVacantesQuery:
    ubicacion: str | None = None
    categoria: str | None = None
    offset: int = 0
    limit: int = 20


class ListarVacantesUseCase:
    """Lista vacantes activas con filtros opcionales de ubicación y categoría (RF-02.2)."""

    def __init__(self, vacantes: VacanteRepositoryPort) -> None:
        self._vacantes = vacantes

    async def execute(self, query: ListarVacantesQuery) -> list[Vacante]:
        limit = min(query.limit, 100)  # cap en 100 para proteger la BD
        return await self._vacantes.list_activas(
            ubicacion=query.ubicacion,
            categoria=query.categoria,
            offset=query.offset,
            limit=limit,
        )
