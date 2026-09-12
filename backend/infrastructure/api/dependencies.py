from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from infrastructure.adapters.persistence.database import get_session
from infrastructure.adapters.persistence.user_repository import SqlAlchemyUserRepository
from infrastructure.adapters.security import JwtTokenService, PasslibPasswordHasher


async def get_user_repository(
    session: AsyncSession = Depends(get_session),
) -> AsyncIterator[SqlAlchemyUserRepository]:
    yield SqlAlchemyUserRepository(session)


def get_password_hasher() -> PasslibPasswordHasher:
    return PasslibPasswordHasher()


def get_token_service() -> JwtTokenService:
    return JwtTokenService()
