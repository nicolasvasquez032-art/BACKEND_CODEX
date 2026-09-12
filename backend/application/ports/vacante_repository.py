from typing import Protocol
from uuid import UUID

from domain.entities.vacante import Vacante, VacanteEstado


class VacanteRepositoryPort(Protocol):

    async def create(
        self,
        empresa_id: UUID,
        titulo: str,
        descripcion: str,
        requisitos: list[str],
        ubicacion: str,
        categoria: str | None,
        salario_min: float | None,
        salario_max: float | None,
    ) -> Vacante:
        raise NotImplementedError

    async def find_by_id(self, vacante_id: UUID) -> Vacante | None:
        raise NotImplementedError

    async def list_activas(
        self,
        ubicacion: str | None = None,
        categoria: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Vacante]:
        raise NotImplementedError

    async def update(
        self,
        vacante_id: UUID,
        titulo: str,
        descripcion: str,
        requisitos: list[str],
        ubicacion: str,
        categoria: str | None,
        salario_min: float | None,
        salario_max: float | None,
    ) -> Vacante:
        raise NotImplementedError

    async def change_estado(self, vacante_id: UUID, nuevo_estado: VacanteEstado) -> Vacante:
        raise NotImplementedError
