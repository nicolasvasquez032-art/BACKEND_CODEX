import hashlib
from dataclasses import dataclass
from datetime import UTC, datetime

from application.ports.password_hasher import PasswordHasherPort
from application.ports.user_repository import UserRepositoryPort
from domain.exceptions import InvalidResetTokenError


@dataclass(frozen=True)
class ConfirmPasswordResetCommand:
    raw_token: str       # Token en texto plano recibido del cliente
    new_password: str    # Nueva contraseña en texto plano


class ConfirmPasswordResetUseCase:
    """Valida el token de reset y actualiza la contraseña del usuario.

    Flujo:
    1. Hashea el token recibido y busca el registro en BD.
    2. Valida que no esté expirado ni ya usado.
    3. Actualiza la contraseña (hasheada con bcrypt).
    4. Marca el token como usado para que no pueda reutilizarse.
    """

    def __init__(
        self,
        users: UserRepositoryPort,
        password_hasher: PasswordHasherPort,
    ) -> None:
        self._users = users
        self._password_hasher = password_hasher

    async def execute(self, command: ConfirmPasswordResetCommand) -> None:
        token_hash = hashlib.sha256(command.raw_token.encode()).hexdigest()

        reset_token = await self._users.find_password_reset_token(token_hash)
        if reset_token is None or not reset_token.is_valid(datetime.now(UTC)):
            raise InvalidResetTokenError("Token inválido o expirado")

        new_hash = self._password_hasher.hash(command.new_password)
        await self._users.update_user_password(
            user_id=reset_token.user_id,
            new_password_hash=new_hash,
        )
        await self._users.mark_token_used(reset_token.id)
