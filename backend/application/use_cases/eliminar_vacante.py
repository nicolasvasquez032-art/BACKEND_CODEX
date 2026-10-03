from dataclasses import dataclass
from uuid import UUID

from application.ports.vacante_repository import VacanteRepositoryPort
from domain.exceptions import PermissionDeniedError, VacanteNotFoundError

@dataclass(frozen=True)
class EliminarVacanteCommand:
    vacante_id: UUID
    requesting_empresa_id: UUID

class EliminarVacanteUseCase:
    def __init__(self, vacante_repo: VacanteRepositoryPort) -> None:
        self._vacante_repo = vacante_repo

    async def execute(self, command: EliminarVacanteCommand) -> None:
        vacante = await self._vacante_repo.find_by_id(command.vacante_id)
        if not vacante:
            raise VacanteNotFoundError(f"Vacante {command.vacante_id} no encontrada")
        
        if vacante.empresa_id != command.requesting_empresa_id:
            raise PermissionDeniedError("No eres el dueño de esta vacante")
            
        await self._vacante_repo.delete(command.vacante_id)
