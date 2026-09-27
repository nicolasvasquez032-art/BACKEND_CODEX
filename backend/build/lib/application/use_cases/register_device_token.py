from uuid import UUID

from application.ports.notificacion_ports import NotificacionRepositoryPort
from domain.entities.notificacion import DeviceToken


class RegisterDeviceTokenUseCase:
    def __init__(self, repository: NotificacionRepositoryPort):
        self.repository = repository

    async def execute(self, usuario_id: UUID, token: str, dispositivo_info: str | None = None) -> DeviceToken:
        device_token = await self.repository.get_device_token_by_usuario_id(usuario_id)
        if device_token:
            device_token.actualizar_token(token, dispositivo_info)
        else:
            device_token = DeviceToken(
                usuario_id=usuario_id,
                token=token,
                dispositivo_info=dispositivo_info
            )
        
        await self.repository.save_device_token(device_token)
        return device_token
