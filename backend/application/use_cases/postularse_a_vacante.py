from dataclasses import dataclass
from uuid import UUID

from application.ports.postulacion_repository import PostulacionRepositoryPort
from application.ports.vacante_repository import VacanteRepositoryPort
from domain.entities.postulacion import Postulacion
from domain.exceptions import (
    DuplicatePostulacionError,
    VacanteNotFoundError,
)


@dataclass(frozen=True)
class PostularseAVacanteCommand:
    candidato_id: UUID     # ID del perfil candidato (perfiles_candidato.id)
    vacante_id: UUID


class PostularseAVacanteUseCase:
    """Registra la postulación de un candidato a una vacante (RF-03.1, RF-03.2).

    Reglas de negocio:
    - La vacante debe estar en estado ACTIVA.
    - No puede existir una postulación previa del mismo candidato a la misma vacante.
    """

    def __init__(
        self,
        postulaciones: PostulacionRepositoryPort,
        vacantes: VacanteRepositoryPort,
    ) -> None:
        self._postulaciones = postulaciones
        self._vacantes = vacantes

    async def execute(self, command: PostularseAVacanteCommand) -> Postulacion:
        vacante = await self._vacantes.find_by_id(command.vacante_id)
        if vacante is None:
            raise VacanteNotFoundError(f"Vacante {command.vacante_id} no encontrada")

        if not vacante.esta_activa():
            raise VacanteNotFoundError(
                f"La vacante '{vacante.titulo}' no está activa y no acepta postulaciones"
            )

        existing = await self._postulaciones.find_by_candidato_and_vacante(
            candidato_id=command.candidato_id,
            vacante_id=command.vacante_id,
        )
        if existing is not None:
            raise DuplicatePostulacionError(
                "Ya existe una postulación para esta vacante"
            )

        return await self._postulaciones.create(
            candidato_id=command.candidato_id,
            vacante_id=command.vacante_id,
        )
