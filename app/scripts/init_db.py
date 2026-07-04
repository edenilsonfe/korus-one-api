"""Create all tables (dev bootstrap). Prefer alembic upgrade in production."""

import asyncio

from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.db.base import Base
import app.models  # noqa: F401


async def init_db() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    print("Schema criado com sucesso.")


if __name__ == "__main__":
    asyncio.run(init_db())
