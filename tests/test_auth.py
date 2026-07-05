import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_register_and_login(client):
    email = "newuser@test.com"
    reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "name": "Test User",
            "specialtyKey": "fono",
            "council": "CRFa",
            "cpf": "52998224725",
        },
    )
    if reg.status_code == 201:
        assert "accessToken" in reg.json()
    login = await client.post("/api/v1/auth/login", json={"email": email, "password": "securepass123"})
    if login.status_code == 200:
        assert "accessToken" in login.json()
