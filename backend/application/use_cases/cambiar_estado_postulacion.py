from dataclasses import dataclass
from uuid import UUID

from application.ports.postulacion_repository import PostulacionRepositoryPort
from application.ports.vacante_repository import VacanteRepositoryPort
from domain.entities.postulacion import Postulacion, PostulacionEstado
from domain.exceptions import (
    InvalidEstadoTransitionError,
    PermissionDeniedError,
    PostulacionNotFoundError,
    VacanteNotFoundError,
)


@dataclass(frozen=True)
class CambiarEstadoPostulacionCommand:
    postulacion_id: UUID
    requesting_empresa_id: UUID   # empresa autenticada
    nuevo_estado: PostulacionEstado


class CambiarEstadoPostulacionUseCase:
    """Avanza el estado de una postulación en el flujo kanban (RF-03.3).

    Reglas de negocio:
    - Solo la empresa dueña de la vacante puede cambiar el estado.
    - Las transiciones deben respetar el flujo: postulado→entrevista|rechazado,
      entrevista→contratado|rechazado.
    """

    def __init__(
        self,
        postulaciones: PostulacionRepositoryPort,
        vacantes: VacanteRepositoryPort,
    ) -> None:
        self._postulaciones = postulaciones
        self._vacantes = vacantes

    async def execute(self, command: CambiarEstadoPostulacionCommand) -> Postulacion:
        postulacion = await self._postulaciones.find_by_id(command.postulacion_id)
        if postulacion is None:
            raise PostulacionNotFoundError(f"Postulación {command.postulacion_id} no encontrada")

        # Verificar que la empresa sea dueña de la vacante asociada
        vacante = await self._vacantes.find_by_id(postulacion.vacante_id)
        if vacante is None:
            raise VacanteNotFoundError("La vacante asociada no existe")

        if not vacante.puede_ser_editada_por(command.requesting_empresa_id):
            raise PermissionDeniedError(
                "Solo la empresa dueña de la vacante puede gestionar sus postulaciones"
            )

        # Validar transición de estado en el dominio
        if not postulacion.puede_cambiar_estado(command.nuevo_estado):
            raise InvalidEstadoTransitionError(
                f"No se puede pasar de '{postulacion.estado}' a '{command.nuevo_estado}'"
            )

        return await self._postulaciones.change_estado(
            postulacion_id=command.postulacion_id,
            nuevo_estado=command.nuevo_estado,
        )
