from uuid import UUID

from application.ports.vacante_repository import VacanteRepositoryPort
from domain.entities.vacante import Vacante, VacanteEstado


class ModerarVacanteUseCase:
    """Cambia el estado de una vacante, utilizado principalmente por administradores."""
    
    def __init__(self, vacantes: VacanteRepositoryPort):
        self._vacantes = vacantes

    async def execute(self, vacante_id: UUID, nuevo_estado: VacanteEstado) -> Vacante:
        # En una arquitectura estricta, el Admin podría enviar una justificación o notificar a la empresa,
        # pero para el requerimiento básico, cambiamos el estado.
        return await self._vacantes.change_estado(vacante_id, nuevo_estado)
