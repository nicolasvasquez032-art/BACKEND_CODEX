from typing import Protocol
from uuid import UUID

from domain.entities.notificacion import DeviceToken, Notificacion


class NotificacionRepositoryPort(Protocol):
    async def get_device_token_by_usuario_id(self, usuario_id: UUID) -> DeviceToken | None:
        ...

    async def save_device_token(self, token: DeviceToken) -> None:
        ...

    async def save_notificacion(self, notificacion: Notificacion) -> None:
        ...

    async def get_notificaciones_by_usuario(
        self, usuario_id: UUID, limit: int = 50, offset: int = 0
    ) -> list[Notificacion]:
        ...

    async def get_notificacion_by_id(self, notificacion_id: UUID) -> Notificacion | None:
        ...


class PushNotificationPort(Protocol):
    async def send_notification(self, token: str, title: str, body: str, data: dict[str, str] | None = None) -> bool:
        ...
