from dataclasses import dataclass, field
from datetime import datetime, UTC
from uuid import UUID, uuid4


@dataclass
class Notificacion:
    usuario_id: UUID
    tipo: str
    mensaje: str
    id: UUID = field(default_factory=uuid4)
    leido: bool = False
    creado_en: datetime = field(default_factory=lambda: datetime.now(UTC))

    def marcar_como_leida(self) -> None:
        self.leido = True


@dataclass
class DeviceToken:
    usuario_id: UUID
    token: str
    dispositivo_info: str | None = None
    id: UUID = field(default_factory=uuid4)
    creado_en: datetime = field(default_factory=lambda: datetime.now(UTC))
    actualizado_en: datetime = field(default_factory=lambda: datetime.now(UTC))

    def actualizar_token(self, nuevo_token: str, dispositivo_info: str | None = None) -> None:
        self.token = nuevo_token
        if dispositivo_info:
            self.dispositivo_info = dispositivo_info
        self.actualizado_en = datetime.now(UTC)
