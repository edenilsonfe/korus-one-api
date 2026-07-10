"""HTTP tests for AI conversation CRUD (title update + delete)."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai import Conversation
from app.models.professional import Professional


@pytest.fixture
async def conversation(db_session: AsyncSession, professional: Professional):
    conv = Conversation(
        professional_id=professional.id,
        title="Conversa original",
    )
    db_session.add(conv)
    await db_session.commit()
    await db_session.refresh(conv)
    return conv


async def test_create_conversation(api_client: AsyncClient, auth_headers: dict):
    resp = await api_client.post(
        "/api/v1/ai/conversations",
        headers=auth_headers,
        json={"title": "Nova conversa"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Nova conversa"
    assert data["messages"] == []
    assert data["id"]


async def test_update_conversation_title(
    api_client: AsyncClient,
    auth_headers: dict,
    conversation: Conversation,
):
    resp = await api_client.patch(
        f"/api/v1/ai/conversations/{conversation.id}",
        headers=auth_headers,
        json={"title": "Novo título"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["title"] == "Novo título"
    assert data["id"] == str(conversation.id)


async def test_update_conversation_rejects_empty_title(
    api_client: AsyncClient,
    auth_headers: dict,
    conversation: Conversation,
):
    resp = await api_client.patch(
        f"/api/v1/ai/conversations/{conversation.id}",
        headers=auth_headers,
        json={"title": "   "},
    )
    assert resp.status_code == 400


async def test_delete_conversation(
    api_client: AsyncClient,
    auth_headers: dict,
    conversation: Conversation,
):
    resp = await api_client.delete(
        f"/api/v1/ai/conversations/{conversation.id}",
        headers=auth_headers,
    )
    assert resp.status_code == 204

    list_resp = await api_client.get("/api/v1/ai/conversations", headers=auth_headers)
    assert list_resp.status_code == 200
    ids = [c["id"] for c in list_resp.json()]
    assert str(conversation.id) not in ids


async def test_delete_conversation_not_found(api_client: AsyncClient, auth_headers: dict):
    resp = await api_client.delete(
        "/api/v1/ai/conversations/00000000-0000-0000-0000-000000000099",
        headers=auth_headers,
    )
    assert resp.status_code == 404
