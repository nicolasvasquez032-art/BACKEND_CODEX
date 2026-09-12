"""Dependencias de FastAPI: sesión de BD, repositorios y usuario autenticado."""
from collections.abc import AsyncIterator
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from domain.entities.user import User, UserRole
from infrastructure.adapters.cv_parser.composite_parser import CompositeCvParser
from infrastructure.adapters.email.smtp_email_service import SmtpEmailService
from infrastructure.adapters.persistence.database import get_session
from infrastructure.adapters.persistence.user_repository import SqlAlchemyUserRepository
from infrastructure.adapters.security import JwtTokenService, PasslibPasswordHasher
from infrastructure.config import settings

_bearer_scheme = HTTPBearer()


async def get_user_repository(
    session: AsyncSession = Depends(get_session),
) -> AsyncIterator[SqlAlchemyUserRepository]:
    yield SqlAlchemyUserRepository(session)


def get_password_hasher() -> PasslibPasswordHasher:
    return PasslibPasswordHasher()


def get_token_service() -> JwtTokenService:
    return JwtTokenService()


def get_email_service() -> SmtpEmailService:
    return SmtpEmailService()


def get_cv_parser() -> CompositeCvParser:
    return CompositeCvParser()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    """Valida el JWT Bearer y devuelve el User autenticado.

    Lanza HTTP 401 si el token es inválido, expirado o el usuario no existe.
    """
    token = credentials.credentials
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = UUID(user_id_str)
    except (JWTError, ValueError):
        raise credentials_exception

    repo = SqlAlchemyUserRepository(session)
    user = await repo.find_by_id(user_id)
    if user is None:
        raise credentials_exception
    return user


def require_role(*roles: UserRole):
    """Dependencia de rol: lanza 403 si el usuario autenticado no tiene uno de los roles dados."""
    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permisos para realizar esta acción",
            )
        return current_user
    return _check
