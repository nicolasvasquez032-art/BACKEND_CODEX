from uuid import UUID

from application.ports.notificacion_ports import NotificacionRepositoryPort


class MarkNotificacionReadUseCase:
    def __init__(self, repository: NotificacionRepositoryPort):
        self.repository = repository

    async def execute(self, notificacion_id: UUID) -> None:
        notificacion = await self.repository.get_notificacion_by_id(notificacion_id)
        if notificacion:
            notificacion.marcar_como_leida()
            await self.repository.save_notificacion(notificacion)
