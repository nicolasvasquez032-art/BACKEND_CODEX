from dataclasses import dataclass
from uuid import UUID

from application.ports.vacante_repository import VacanteRepositoryPort
from domain.entities.vacante import Vacante, VacanteEstado
from domain.exceptions import PermissionDeniedError, VacanteNotFoundError


@dataclass(frozen=True)
class CambiarEstadoVacanteCommand:
    vacante_id: UUID
    requesting_empresa_id: UUID
    nuevo_estado: VacanteEstado


class CambiarEstadoVacanteUseCase:
    """Cambia el estado de una vacante: activa ↔ pausada → cerrada (RF-02.3).

    Solo la empresa dueña puede cambiar el estado.
    """

    def __init__(self, vacantes: VacanteRepositoryPort) -> None:
        self._vacantes = vacantes

    async def execute(self, command: CambiarEstadoVacanteCommand) -> Vacante:
        vacante = await self._vacantes.find_by_id(command.vacante_id)
        if vacante is None:
            raise VacanteNotFoundError(f"Vacante {command.vacante_id} no encontrada")

        if not vacante.puede_ser_editada_por(command.requesting_empresa_id):
            raise PermissionDeniedError("Solo la empresa dueña puede cambiar el estado")

        return await self._vacantes.change_estado(
            vacante_id=command.vacante_id,
            nuevo_estado=command.nuevo_estado,
        )
