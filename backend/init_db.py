import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from infrastructure.adapters.persistence.models import Base
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://talentmatch:talentmatch@postgres:5432/talentmatch")

async def init_models():
    engine = create_async_engine(DATABASE_URL, echo=True)
    async with engine.begin() as conn:
        # Create extension vector if not exists
        await conn.execute(from_sqlalchemy_text("CREATE EXTENSION IF NOT EXISTS vector;"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Database initialized successfully.")

if __name__ == "__main__":
    from sqlalchemy import text as from_sqlalchemy_text
    asyncio.run(init_models())
