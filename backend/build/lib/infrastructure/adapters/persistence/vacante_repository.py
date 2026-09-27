from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.vacante import Vacante, VacanteEstado
from infrastructure.adapters.persistence.models import VacanteModel


class SqlAlchemyVacanteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

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
        latitud: float | None = None,
        longitud: float | None = None,
    ) -> Vacante:
        model = VacanteModel(
            empresa_id=empresa_id,
            titulo=titulo,
            descripcion=descripcion,
            requisitos=requisitos,
            ubicacion=ubicacion,
            categoria=categoria,
            salario_min=salario_min,
            salario_max=salario_max,
            latitud=latitud,
            longitud=longitud,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def find_by_id(self, vacante_id: UUID) -> Vacante | None:
        model = await self._session.get(VacanteModel, vacante_id)
        return self._to_entity(model) if model else None

    async def list_activas(
        self,
        ubicacion: str | None = None,
        categoria: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Vacante]:
        stmt = select(VacanteModel).where(VacanteModel.estado == VacanteEstado.ACTIVA)
        if ubicacion:
            stmt = stmt.where(VacanteModel.ubicacion.ilike(f"%{ubicacion}%"))
        if categoria:
            stmt = stmt.where(VacanteModel.categoria.ilike(f"%{categoria}%"))
        stmt = stmt.order_by(VacanteModel.creado_en.desc()).offset(offset).limit(limit)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

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
        model = await self._session.get(VacanteModel, vacante_id)
        if model is None:
            raise ValueError(f"Vacante {vacante_id} no encontrada en BD")
        model.titulo = titulo
        model.descripcion = descripcion
        model.requisitos = requisitos
        model.ubicacion = ubicacion
        model.categoria = categoria
        model.salario_min = salario_min
        model.salario_max = salario_max
        await self._session.flush()
        return self._to_entity(model)

    async def change_estado(self, vacante_id: UUID, nuevo_estado: VacanteEstado) -> Vacante:
        model = await self._session.get(VacanteModel, vacante_id)
        if model is None:
            raise ValueError(f"Vacante {vacante_id} no encontrada en BD")
        model.estado = nuevo_estado
        await self._session.flush()
        return self._to_entity(model)

    async def update_embedding(self, vacante_id: UUID, embedding: list[float]) -> None:
        model = await self._session.get(VacanteModel, vacante_id)
        if model:
            model.embedding = embedding
            await self._session.commit()

    @staticmethod
    def _to_entity(model: VacanteModel) -> Vacante:
        return Vacante(
            id=model.id,
            empresa_id=model.empresa_id,
            titulo=model.titulo,
            descripcion=model.descripcion,
            requisitos=list(model.requisitos),
            ubicacion=model.ubicacion,
            estado=model.estado,
            creado_en=model.creado_en,
            categoria=model.categoria,
            salario_min=model.salario_min,
            salario_max=model.salario_max,
            latitud=model.latitud,
            longitud=model.longitud,
        )
