from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.postulacion import Postulacion, PostulacionEstado
from infrastructure.adapters.persistence.models import PostulacionModel


class SqlAlchemyPostulacionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, candidato_id: UUID, vacante_id: UUID) -> Postulacion:
        model = PostulacionModel(candidato_id=candidato_id, vacante_id=vacante_id)
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def find_by_id(self, postulacion_id: UUID) -> Postulacion | None:
        model = await self._session.get(PostulacionModel, postulacion_id)
        return self._to_entity(model) if model else None

    async def find_by_candidato_and_vacante(
        self,
        candidato_id: UUID,
        vacante_id: UUID,
    ) -> Postulacion | None:
        result = await self._session.execute(
            select(PostulacionModel).where(
                PostulacionModel.candidato_id == candidato_id,
                PostulacionModel.vacante_id == vacante_id,
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_by_candidato(self, candidato_id: UUID) -> list[Postulacion]:
        result = await self._session.execute(
            select(PostulacionModel)
            .where(PostulacionModel.candidato_id == candidato_id)
            .order_by(PostulacionModel.fecha.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_by_vacante(self, vacante_id: UUID) -> list[Postulacion]:
        result = await self._session.execute(
            select(PostulacionModel)
            .where(PostulacionModel.vacante_id == vacante_id)
            .order_by(PostulacionModel.fecha.desc())
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def change_estado(
        self,
        postulacion_id: UUID,
        nuevo_estado: PostulacionEstado,
    ) -> Postulacion:
        model = await self._session.get(PostulacionModel, postulacion_id)
        if model is None:
            raise ValueError(f"Postulación {postulacion_id} no encontrada en BD")
        model.estado = nuevo_estado
        await self._session.flush()
        return self._to_entity(model)

    @staticmethod
    def _to_entity(model: PostulacionModel) -> Postulacion:
        return Postulacion(
            id=model.id,
            candidato_id=model.candidato_id,
            vacante_id=model.vacante_id,
            estado=model.estado,
            fecha=model.fecha,
            score_match=model.score_match,
        )
