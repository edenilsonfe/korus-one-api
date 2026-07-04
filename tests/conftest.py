import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import hash_password
from app.db.base import Base
import app.models  # noqa: F401
from app.main import app
from app.models.professional import Professional

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine):
    session_factory = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session


@pytest.fixture
async def auth_headers(db_session):
    professional = Professional(
        email="test@example.com",
        password_hash=hash_password("testpass123"),
        name="Test Professional",
        specialty="Fono",
        council="CRFa",
    )
    db_session.add(professional)
    await db_session.commit()

    from app.core.security import create_access_token

    token = create_access_token(professional.id)
    return {"Authorization": f"Bearer {token}"}
