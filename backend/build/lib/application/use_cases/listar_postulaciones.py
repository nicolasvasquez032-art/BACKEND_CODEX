from dataclasses import dataclass
from uuid import UUID

from application.ports.postulacion_repository import PostulacionRepositoryPort
from domain.entities.postulacion import Postulacion


@dataclass(frozen=True)
class ListarPostulacionesCandidatoQuery:
    candidato_id: UUID
    requesting_user_id: UUID
    requesting_user_role: str


class ListarPostulacionesCandidatoUseCase:
    """Retorna el historial de postulaciones de un candidato (RF-03.4).

    El candidato solo puede ver sus propias postulaciones.
    Las empresas y administradores pueden ver las de cualquier candidato.
    """

    def __init__(self, postulaciones: PostulacionRepositoryPort) -> None:
        self._postulaciones = postulaciones

    async def execute(self, query: ListarPostulacionesCandidatoQuery) -> list[Postulacion]:
        from domain.exceptions import PermissionDeniedError
        if (
            query.requesting_user_role == "candidate"
            and query.requesting_user_id != query.candidato_id
        ):
            raise PermissionDeniedError("Solo puedes ver tus propias postulaciones")

        return await self._postulaciones.list_by_candidato(query.candidato_id)


@dataclass(frozen=True)
class ListarPostulacionesVacanteQuery:
    vacante_id: UUID
    requesting_empresa_id: UUID


class ListarPostulacionesVacanteUseCase:
    """Retorna las postulaciones recibidas para una vacante (RF-03.3).

    Solo la empresa dueña de la vacante puede ver sus postulaciones.
    """

    def __init__(
        self,
        postulaciones: PostulacionRepositoryPort,
        vacantes,  # VacanteRepositoryPort — evitamos importar para no crear ciclos
    ) -> None:
        self._postulaciones = postulaciones
        self._vacantes = vacantes

    async def execute(self, query: ListarPostulacionesVacanteQuery) -> list[Postulacion]:
        from domain.exceptions import PermissionDeniedError, VacanteNotFoundError
        vacante = await self._vacantes.find_by_id(query.vacante_id)
        if vacante is None:
            raise VacanteNotFoundError(f"Vacante {query.vacante_id} no encontrada")
        if not vacante.puede_ser_editada_por(query.requesting_empresa_id):
            raise PermissionDeniedError("Solo la empresa dueña puede ver las postulaciones")
        return await self._postulaciones.list_by_vacante(query.vacante_id)
