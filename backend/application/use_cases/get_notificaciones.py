from uuid import UUID

from application.ports.notificacion_ports import NotificacionRepositoryPort
from domain.entities.notificacion import Notificacion


class GetNotificacionesUseCase:
    def __init__(self, repository: NotificacionRepositoryPort):
        self.repository = repository

    async def execute(self, usuario_id: UUID, limit: int = 50, offset: int = 0) -> list[Notificacion]:
        return await self.repository.get_notificaciones_by_usuario(
            usuario_id=usuario_id,
            limit=limit,
            offset=offset
        )
