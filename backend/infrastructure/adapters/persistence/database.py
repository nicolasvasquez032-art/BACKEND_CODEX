from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from infrastructure.config import settings


class Base(DeclarativeBase):
    pass


# Configuración de connect_args para compatibilidad con PgBouncer en Transaction Pooling
connect_args: dict[str, Any] = {}
if settings.use_pgbouncer or "pgbouncer" in settings.database_url:
    # Deshabilitar statement cache en asyncpg para permitir que PgBouncer multiplexe conexiones
    connect_args["statement_cache_size"] = 0

# Pool Principal de Escrituras (Writer Primary DB / PgBouncer)
writer_engine = create_async_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_timeout=settings.db_pool_timeout,
    connect_args=connect_args,
)
writer_session_factory = async_sessionmaker(writer_engine, expire_on_commit=False)

# Pool de Réplica de Solo Lectura (Read Replica DB)
# Si no hay réplica configurada, reutiliza transparentemente el pool del writer
if settings.database_read_replica_url:
    read_connect_args: dict[str, Any] = {}
    if settings.use_pgbouncer or "pgbouncer" in settings.database_read_replica_url:
        read_connect_args["statement_cache_size"] = 0
    reader_engine = create_async_engine(
        settings.database_read_replica_url,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        connect_args=read_connect_args,
    )
    reader_session_factory = async_sessionmaker(reader_engine, expire_on_commit=False)
else:
    reader_engine = writer_engine
    reader_session_factory = writer_session_factory

# Alias retrocompatibles
engine = writer_engine
session_factory = writer_session_factory


async def get_session() -> AsyncIterator[AsyncSession]:
    """Sesión con permisos de escritura apuntando a la base de datos primaria."""
    async with writer_session_factory() as session:
        yield session


async def get_read_session() -> AsyncIterator[AsyncSession]:
    """Sesión optimizada de solo lectura apuntando a la réplica de lectura (Read Replica)."""
    async with reader_session_factory() as session:
        yield session
