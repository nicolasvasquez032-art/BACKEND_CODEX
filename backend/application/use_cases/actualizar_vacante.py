from dataclasses import dataclass
from uuid import UUID

from application.ports.vacante_repository import VacanteRepositoryPort
from domain.entities.vacante import Vacante
from domain.exceptions import PermissionDeniedError, VacanteNotFoundError


@dataclass(frozen=True)
class ActualizarVacanteCommand:
    vacante_id: UUID
    requesting_empresa_id: UUID   # empresa autenticada
    titulo: str
    descripcion: str
    requisitos: list[str]
    ubicacion: str
    categoria: str | None = None
    salario_min: float | None = None
    salario_max: float | None = None


class ActualizarVacanteUseCase:
    """Actualiza los datos de una vacante. Solo la empresa dueña puede editarla (RF-02.3)."""

    def __init__(self, vacantes: VacanteRepositoryPort) -> None:
        self._vacantes = vacantes

    async def execute(self, command: ActualizarVacanteCommand) -> Vacante:
        vacante = await self._vacantes.find_by_id(command.vacante_id)
        if vacante is None:
            raise VacanteNotFoundError(f"Vacante {command.vacante_id} no encontrada")

        if not vacante.puede_ser_editada_por(command.requesting_empresa_id):
            raise PermissionDeniedError("Solo la empresa dueña puede editar esta vacante")

        return await self._vacantes.update(
            vacante_id=command.vacante_id,
            titulo=command.titulo,
            descripcion=command.descripcion,
            requisitos=command.requisitos,
            ubicacion=command.ubicacion,
            categoria=command.categoria,
            salario_min=command.salario_min,
            salario_max=command.salario_max,
        )
