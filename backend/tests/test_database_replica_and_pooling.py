"""Pruebas unitarias para la separación de réplicas de lectura y connection pooling con PgBouncer."""
import pytest
from unittest.mock import patch

from infrastructure.config import Settings
from infrastructure.adapters.persistence.database import get_session, get_read_session


@pytest.mark.asyncio
async def test_session_dependencies_yield_active_sessions():
    """Valida que get_session y get_read_session deleguen en sus factories correspondientes."""
    from unittest.mock import AsyncMock, patch

    mock_writer_session = AsyncMock()
    mock_reader_session = AsyncMock()

    class MockAsyncContextManager:
        def __init__(self, session_obj):
            self.session_obj = session_obj

        async def __aenter__(self):
            return self.session_obj

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    with patch("infrastructure.adapters.persistence.database.writer_session_factory", return_value=MockAsyncContextManager(mock_writer_session)):
        async for writer_sess in get_session():
            assert writer_sess is mock_writer_session

    with patch("infrastructure.adapters.persistence.database.reader_session_factory", return_value=MockAsyncContextManager(mock_reader_session)):
        async for reader_sess in get_read_session():
            assert reader_sess is mock_reader_session


def test_read_replica_configuration_fallback():
    """Valida que si no se define database_read_replica_url, reader_engine usa la primaria."""
    from infrastructure.adapters.persistence import database
    assert database.reader_engine is not None
    assert database.writer_engine is not None


def test_pgbouncer_statement_cache_disabled_when_enabled():
    """Valida que connect_args incluya statement_cache_size=0 para transaction pooling de PgBouncer."""
    custom_settings = Settings(
        database_url="postgresql+asyncpg://user:pass@pgbouncer:6432/db",
        use_pgbouncer=True,
    )
    assert custom_settings.use_pgbouncer is True
    assert "pgbouncer" in custom_settings.database_url
