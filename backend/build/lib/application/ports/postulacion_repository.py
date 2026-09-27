from typing import Protocol
from uuid import UUID

from domain.entities.postulacion import Postulacion, PostulacionEstado


class PostulacionRepositoryPort(Protocol):

    async def create(
        self,
        candidato_id: UUID,
        vacante_id: UUID,
    ) -> Postulacion:
        raise NotImplementedError

    async def find_by_id(self, postulacion_id: UUID) -> Postulacion | None:
        raise NotImplementedError

    async def find_by_candidato_and_vacante(
        self,
        candidato_id: UUID,
        vacante_id: UUID,
    ) -> Postulacion | None:
        raise NotImplementedError

    async def list_by_candidato(self, candidato_id: UUID) -> list[Postulacion]:
        raise NotImplementedError

    async def list_by_vacante(self, vacante_id: UUID) -> list[Postulacion]:
        raise NotImplementedError

    async def change_estado(
        self,
        postulacion_id: UUID,
        nuevo_estado: PostulacionEstado,
    ) -> Postulacion:
        raise NotImplementedError
