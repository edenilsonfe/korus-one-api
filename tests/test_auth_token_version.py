import pytest
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.compiler import compiles

from app.core.security import create_access_token
from app.models.professional import Professional

from sqlalchemy.ext.asyncio import AsyncSession


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kw):
    return "JSON"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(_type, _compiler, **_kw):
    return "JSON"


@pytest.mark.asyncio
async def test_access_token_with_current_version_is_accepted(api_client, professional):
    token = create_access_token(professional.id, token_version=professional.token_version)

    response = await api_client.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_access_token_with_stale_version_is_rejected(
    api_client, db_session: AsyncSession, professional: Professional
):
    token = create_access_token(professional.id, token_version=0)
    professional.token_version = 1
    db_session.add(professional)
    await db_session.commit()

    response = await api_client.get(
        "/api/v1/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Sessão invalidada. Faça login novamente."
