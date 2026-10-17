from datetime import UTC, datetime, timedelta

from jose import jwt

from domain.entities.user import User
from infrastructure.config import settings


class JwtTokenService:
    def create_access_token(self, user: User) -> str:
        expires_at = datetime.now(UTC) + timedelta(
            minutes=settings.jwt_access_token_expire_minutes
        )
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "role": user.role.value,
            "is_premium": user.is_premium,
            "type": "access",
            "exp": expires_at,
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    def create_refresh_token(self, user: User) -> str:
        expires_at = datetime.now(UTC) + timedelta(
            days=settings.jwt_refresh_token_expire_days
        )
        payload = {
            "sub": str(user.id),
            "email": user.email,
            "type": "refresh",
            "exp": expires_at,
        }
        return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    def decode_token(self, token: str) -> dict:
        return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])

