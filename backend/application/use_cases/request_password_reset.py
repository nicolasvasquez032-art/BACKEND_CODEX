import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from application.ports.email_service import EmailServicePort
from application.ports.user_repository import UserRepositoryPort
from domain.exceptions import UserNotFoundError

# El token expira en 1 hora
_RESET_TOKEN_EXPIRE_HOURS = 1


@dataclass(frozen=True)
class RequestPasswordResetCommand:
    email: str
    frontend_url: str  # base URL del frontend, p. ej. "https://talentmatch.app"


class RequestPasswordResetUseCase:
    """Genera un token de recuperación de contraseña y lo envía por correo.

    El token real (aleatorio) nunca se almacena; solo su hash SHA-256 se guarda
    en la base de datos para evitar que un atacante que lea la BD pueda usarlo.
    """

    def __init__(
        self,
        users: UserRepositoryPort,
        email_service: EmailServicePort,
    ) -> None:
        self._users = users
        self._email_service = email_service

    async def execute(self, command: RequestPasswordResetCommand) -> None:
        user = await self._users.find_by_email(command.email)
        if user is None:
            # Respuesta silenciosa para no revelar si el email existe
            return

        # Generar token seguro
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        expires_at = datetime.now(UTC) + timedelta(hours=_RESET_TOKEN_EXPIRE_HOURS)

        await self._users.create_password_reset_token(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )

        reset_link = f"{command.frontend_url}/auth/reset-password?token={raw_token}"
        await self._email_service.send_password_reset(
            to_email=command.email,
            reset_link=reset_link,
        )
