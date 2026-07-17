"""Tests for generic battery creation with module selection."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.session import get_db
from app.main import app


@pytest.mark.asyncio
async def test_create_battery_with_selected_modules(
    db_session, professional, patient, auth_headers,
):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/batteries",
            headers=auth_headers,
            json={
                "instrumentSlug": "abfw",
                "patientId": str(patient.id),
                "moduleSlugs": ["fonologia-nomeacao"],
            },
        )

    app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert len(body["subforms"]) == 1
    assert body["subforms"][0]["subformSlug"] == "fonologia-nomeacao"
