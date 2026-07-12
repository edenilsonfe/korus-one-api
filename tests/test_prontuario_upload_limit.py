"""Regression test for the prontuario attachment upload size cap (413).

Standalone setup: creates only the tables needed on an in-memory SQLite DB,
mirroring the pattern in test_session_evolutions_idor.py /
test_speech_analysis_ownership.py. `EntitlementMiddleware` opens its own
session directly from `AsyncSessionLocal` (not the FastAPI `get_db`
override), so it is monkeypatched to the same in-memory engine too —
this test must never touch the real Postgres instance.
"""

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from app.core.config import get_settings
from app.core.security import create_access_token
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.attachment import Attachment
from app.models.patient import Patient
from app.models.professional import Professional


# Patient.diagnosis_keys is a Postgres JSONB column; SQLAlchemy 2.x can't
# render it for SQLite CREATE TABLE. Map it to plain JSON for this
# in-memory test DB only (same shim as test_session_evolutions_idor.py).
@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(element, compiler, **kw):
    return "JSON"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(element, compiler, **kw):
    return "JSON"


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_MAX_UPLOAD_BYTES = 16


async def _engine():
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                bind=sync_conn,
                tables=[
                    Professional.__table__,
                    Patient.__table__,
                    Attachment.__table__,
                ],
            )
        )
    return eng


async def _make_professional(db, *, email):
    pro = Professional(
        email=email,
        password_hash="x",
        name="Dra. Teste",
        specialty_key="fono",
        specialty="Fonoaudiologia",
        council="CRFa",
        phone="11999990000",
    )
    db.add(pro)
    await db.commit()
    await db.refresh(pro)
    return pro


async def _make_patient(db, professional, *, name):
    p = Patient(
        professional_id=professional.id,
        name=name,
        birth_date=date.today().replace(year=date.today().year - 4),
        diagnosis_keys=["tea"],
        status="ativo",
        start_date=date.today() - timedelta(days=90),
        avatar_color="oklch(0.58 0.12 205)",
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


def _auth_headers(professional):
    return {"Authorization": f"Bearer {create_access_token(professional.id)}"}


async def _client(engine, monkeypatch):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _get_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db
    # EntitlementMiddleware bypasses the get_db override and opens its own
    # session from AsyncSessionLocal — point it at the same test engine so
    # this test never touches the real Postgres instance.
    monkeypatch.setattr("app.middleware.entitlement.AsyncSessionLocal", factory)
    monkeypatch.setattr(get_settings(), "max_upload_bytes", TEST_MAX_UPLOAD_BYTES)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _clear_override():
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.asyncio
async def test_upload_over_limit_returns_413_and_skips_storage(monkeypatch):
    engine = await _engine()
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        pro = await _make_professional(db, email="pro-upload-a@example.com")
        patient = await _make_patient(db, pro, name="Paciente A")

    client = await _client(engine, monkeypatch)
    oversized = b"x" * (TEST_MAX_UPLOAD_BYTES + 1)
    async with client:
        with patch("app.api.v1.prontuario.storage_service.upload", new_callable=AsyncMock) as mock_upload:
            resp = await client.post(
                f"/api/v1/patients/{patient.id}/attachments",
                files={"file": ("laudo.pdf", oversized, "application/pdf")},
                headers=_auth_headers(pro),
            )
        assert resp.status_code == 413
        assert "tamanho máximo" in resp.json()["detail"]
        mock_upload.assert_not_called()
    _clear_override()
    await engine.dispose()


@pytest.mark.asyncio
async def test_upload_under_limit_succeeds(monkeypatch):
    engine = await _engine()
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as db:
        pro = await _make_professional(db, email="pro-upload-b@example.com")
        patient = await _make_patient(db, pro, name="Paciente B")

    client = await _client(engine, monkeypatch)
    body = b"x" * TEST_MAX_UPLOAD_BYTES
    async with client:
        with patch("app.api.v1.prontuario.storage_service.upload", new_callable=AsyncMock) as mock_upload:
            resp = await client.post(
                f"/api/v1/patients/{patient.id}/attachments",
                files={"file": ("laudo.pdf", body, "application/pdf")},
                headers=_auth_headers(pro),
            )
        assert resp.status_code == 201
        assert resp.json()["sizeBytes"] == len(body)
        mock_upload.assert_called_once()
    _clear_override()
    await engine.dispose()
