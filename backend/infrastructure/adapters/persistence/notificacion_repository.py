from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from application.ports.notificacion_ports import NotificacionRepositoryPort
from domain.entities.notificacion import DeviceToken, Notificacion
from infrastructure.adapters.persistence.models import DeviceTokenModel, NotificacionModel


class SqlAlchemyNotificacionRepository(NotificacionRepositoryPort):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_device_token_by_usuario_id(self, usuario_id: UUID) -> DeviceToken | None:
        stmt = select(DeviceTokenModel).where(DeviceTokenModel.usuario_id == usuario_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return DeviceToken(
            id=model.id,
            usuario_id=model.usuario_id,
            token=model.token,
            dispositivo_info=model.dispositivo_info,
            creado_en=model.creado_en,
            actualizado_en=model.actualizado_en
        )

    async def save_device_token(self, token: DeviceToken) -> None:
        stmt = select(DeviceTokenModel).where(DeviceTokenModel.id == token.id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            model = DeviceTokenModel(
                id=token.id,
                usuario_id=token.usuario_id,
                token=token.token,
                dispositivo_info=token.dispositivo_info,
                creado_en=token.creado_en,
                actualizado_en=token.actualizado_en
            )
            self.session.add(model)
        else:
            model.token = token.token
            model.dispositivo_info = token.dispositivo_info
            model.actualizado_en = token.actualizado_en
        
        await self.session.commit()

    async def save_notificacion(self, notificacion: Notificacion) -> None:
        stmt = select(NotificacionModel).where(NotificacionModel.id == notificacion.id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()

        if not model:
            model = NotificacionModel(
                id=notificacion.id,
                usuario_id=notificacion.usuario_id,
                tipo=notificacion.tipo,
                mensaje=notificacion.mensaje,
                leido=notificacion.leido,
                creado_en=notificacion.creado_en
            )
            self.session.add(model)
        else:
            model.leido = notificacion.leido
        
        await self.session.commit()

    async def get_notificaciones_by_usuario(
        self, usuario_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[Notificacion]:
        stmt = (
            select(NotificacionModel)
            .where(NotificacionModel.usuario_id == usuario_id)
            .order_by(NotificacionModel.creado_en.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.execute(stmt)
        models = result.scalars().all()
        return [
            Notificacion(
                id=m.id,
                usuario_id=m.usuario_id,
                tipo=m.tipo,
                mensaje=m.mensaje,
                leido=m.leido,
                creado_en=m.creado_en
            )
            for m in models
        ]

    async def get_notificacion_by_id(self, notificacion_id: UUID) -> Notificacion | None:
        stmt = select(NotificacionModel).where(NotificacionModel.id == notificacion_id)
        result = await self.session.execute(stmt)
        model = result.scalar_one_or_none()
        if not model:
            return None
        return Notificacion(
            id=model.id,
            usuario_id=model.usuario_id,
            tipo=model.tipo,
            mensaje=model.mensaje,
            leido=model.leido,
            creado_en=model.creado_en
        )
