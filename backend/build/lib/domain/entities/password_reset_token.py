from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True)
class PasswordResetToken:
    """Entidad de dominio que representa un token de recuperación de contraseña.

    El token almacenado es siempre el hash SHA-256 del token original,
    nunca el token en texto plano.
    """

    id: UUID
    user_id: UUID
    token_hash: str          # SHA-256 del token original
    expires_at: datetime
    used: bool = False

    def is_valid(self, now: datetime) -> bool:
        """Retorna True si el token no ha expirado y no ha sido usado."""
        return not self.used and now < self.expires_at
