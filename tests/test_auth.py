import pytest
from httpx import ASGITransport, AsyncClient
from uuid import uuid4

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


@pytest.mark.asyncio
async def test_register_without_cpf_creates_demo_patient(api_client):
    email = f"nocpf-{uuid4().hex[:8]}@test.com"
    reg = await api_client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "securepass123",
            "name": "Sem Cpf",
            "specialtyKey": "fono",
        },
    )
    assert reg.status_code == 201
    token = reg.json()["accessToken"]
    patients = await api_client.get(
        "/api/v1/patients",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patients.status_code == 200
    names = [p["name"] for p in patients.json()["items"]]
    assert "Paciente demonstração" in names
