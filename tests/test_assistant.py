"""Tests for the unified AI assistant orchestration (LLM mocked).

Standalone setup: creates only the tables needed on an in-memory SQLite DB.
The LLM client is mocked so we never call OpenCode (and never get billed).
Validates: direct tool-call path, no-tool → retry → tool, no-tool → retry →
no-tool → fallback, leaked-markup sanitization, patient ownership guard, and
search_patient_by_name scoping.
"""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.ai import ChatMessage, Conversation
from app.models.appointment import Appointment
from app.models.evolution import Evolution
from app.models.goal import Goal, ClinicalDomainSnapshot
from app.models.patient import Patient
from app.models.professional import Professional
from app.models.session import Session
# NOTE: Assessment/ProtocolCatalog use JSONB columns that SQLite can't render
# in CREATE TABLE on newer SQLAlchemy versions. The production tests run on
# PostgreSQL via the project conftest; here we exclude those tables and test
# get_patient_context only for the ownership-guard path (which short-circuits
# before any Assessment query).
from app.schemas.assistant import ChatResponse
from app.services.assistant.assistant_service import AssistantService
from app.services.assistant.tools import ToolExecutor

pytestmark = pytest.mark.asyncio

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(
            lambda sync_conn: Base.metadata.create_all(
                bind=sync_conn,
                tables=[
                    Professional.__table__,
                    Patient.__table__,
                    Appointment.__table__,
                    Session.__table__,
                    Evolution.__table__,
                    Goal.__table__,
                    ClinicalDomainSnapshot.__table__,
                    Conversation.__table__,
                    ChatMessage.__table__,
                ],
            )
        )
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db(engine):
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


async def _make_professional(db, *, email="prof@x.com", specialty="fono"):
    pro = Professional(
        email=email,
        password_hash="x",
        name="Dra. Teste",
        specialty_key=specialty,
        specialty="Fonoaudiologia",
        council="CRFa",
        phone="11999990000",
    )
    db.add(pro)
    await db.commit()
    await db.refresh(pro)
    return pro


async def _make_patient(db, professional, *, name="João", status="ativo"):
    p = Patient(
        professional_id=professional.id,
        name=name,
        birth_date=date.today().replace(year=date.today().year - 4),
        diagnosis_keys=["tea"],
        status=status,
        start_date=date.today() - timedelta(days=90),
        avatar_color="oklch(0.58 0.12 205)",
    )
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return p


async def _make_conversation(db, professional, patient=None):
    conv = Conversation(
        professional_id=professional.id,
        patient_id=patient.id if patient else None,
        title="Conv",
    )
    db.add(conv)
    await db.commit()
    await db.refresh(conv)
    # eager-load messages attribute as an empty list for the service
    conv.messages = []
    return conv


def _history(conv, content):
    """Append a user message to the conversation in-memory (mirrors handler)."""
    msg = ChatMessage(conversation_id=conv.id, role="user", content=content)
    conv.messages = list(conv.messages or []) + [msg]
    return conv


def _mock_tool_call_msg(name, args, call_id="call_1"):
    """Build an assistant 'message' with tool_calls, like the OpenAI SDK returns."""
    fn = MagicMock()
    fn.name = name
    import json

    fn.arguments = json.dumps(args)
    tc = MagicMock()
    tc.id = call_id
    tc.function = fn
    msg = MagicMock()
    msg.tool_calls = [tc]
    msg.content = None
    choice = MagicMock()
    choice.message = msg
    completion = MagicMock()
    completion.choices = [choice]
    return completion


def _mock_text_msg(text):
    """Build an assistant 'message' with content and no tool_calls."""
    msg = MagicMock()
    msg.tool_calls = None
    msg.content = text
    choice = MagicMock()
    choice.message = msg
    completion = MagicMock()
    completion.choices = [choice]
    return completion


# --------------------------------------------------------------------------- #
# Tests
# --------------------------------------------------------------------------- #


async def test_direct_tool_call_executes_and_returns(db):
    pro = await _make_professional(db)
    p = await _make_patient(db, pro)
    # Seed a session so get_appointment_kpis(completion) returns something.
    db.add(Session(
        patient_id=p.id, professional_id=pro.id,
        date=datetime.now(timezone.utc), duration=45, type="atendimento",
        objectives=[], notes="",
    ))
    await db.commit()

    conv = await _make_conversation(db, pro)
    _history(conv, "Quantas sessões realizei este mês?")

    service = AssistantService(db, pro, conv, llm_client=AsyncMock())
    # 1st call: model calls a tool. 2nd call: final text reply.
    service._call_tool_selection = AsyncMock(
        return_value=_mock_tool_call_msg("get_appointment_kpis", {"metric": "completion"})
    )
    service._call_final = AsyncMock(return_value="Você realizou 1 sessão neste mês.")

    resp = await service.chat("Quantas sessões realizei este mês?")
    assert resp.reply == "Você realizou 1 sessão neste mês."
    assert "get_appointment_kpis" in resp.metadata.tools_used
    assert resp.suggestions is None


async def test_no_tool_then_retry_calls_tool(db):
    pro = await _make_professional(db)
    p = await _make_patient(db, pro)
    conv = await _make_conversation(db, pro)
    _history(conv, "como está minha clínica")

    service = AssistantService(db, pro, conv, llm_client=AsyncMock())
    calls = {"tool_select": 0, "final": 0}
    direct = _mock_text_msg("panorama segue normal")  # 1st: no tool_calls
    retry = _mock_tool_call_msg("get_dashboard_stats", {})  # retry: calls tool
    final = "Sua clínica tem 1 paciente ativo."

    async def _ts(messages, temperature=0.2):
        calls["tool_select"] += 1
        return direct if calls["tool_select"] == 1 else retry

    async def _tf(messages, temperature=0.3):
        calls["final"] += 1
        return final

    service._call_tool_selection = _ts
    service._call_final = _tf

    resp = await service.chat("como está minha clínica")
    assert resp.reply == final
    assert "get_dashboard_stats" in resp.metadata.tools_used
    assert calls["tool_select"] == 2  # direct + retry


async def test_no_tool_no_retry_falls_back(db):
    pro = await _make_professional(db)
    conv = await _make_conversation(db, pro)
    _history(conv, "qual o sentido da vida")

    service = AssistantService(db, pro, conv, llm_client=AsyncMock())
    service._call_tool_selection = AsyncMock(return_value=_mock_text_msg("não sei"))
    service._call_final = AsyncMock(return_value="não deveria chegar aqui")

    resp = await service.chat("qual o sentido da vida")
    assert "Não consigo responder" in resp.reply
    assert resp.metadata.tools_used == []
    assert resp.suggestions is not None and len(resp.suggestions) > 0


async def test_leaked_markup_in_final_falls_back(db):
    pro = await _make_professional(db)
    p = await _make_patient(db, pro)
    conv = await _make_conversation(db, pro)
    _history(conv, "sessões")

    service = AssistantService(db, pro, conv, llm_client=AsyncMock())
    service._call_tool_selection = AsyncMock(
        return_value=_mock_tool_call_msg("get_appointment_kpis", {"metric": "all"})
    )
    # Final reply leaks tool markup → must be replaced by fallback.
    service._call_final = AsyncMock(return_value="<|tool_call|>get_dashboard_stats()")

    resp = await service.chat("sessões")
    assert "<|tool_call" not in resp.reply
    assert "Não consigo responder" in resp.reply  # sanitize of markup → '' → fallback


async def test_tool_leaked_in_first_response_handled(db):
    pro = await _make_professional(db)
    conv = await _make_conversation(db, pro)
    _history(conv, "teste")

    service = AssistantService(db, pro, conv, llm_client=AsyncMock())
    # 1st response leaks markup (no tool_calls). Retry: no tool. → fallback.
    service._call_tool_selection = AsyncMock(
        side_effect=[_mock_text_msg("<|tool_call|>foo"), _mock_text_msg("ainda sem tool")]
    )
    service._call_final = AsyncMock()

    resp = await service.chat("teste")
    assert resp.metadata.tools_used == []
    assert "Não consigo responder" in resp.reply


async def test_patient_ownership_guard_in_tool_executor(db):
    pro = await _make_professional(db)
    other_pro = await _make_professional(db, email="other@x.com")
    # Patient belongs to other_pro.
    other_patient = await _make_patient(db, other_pro, name="Pertence a outro")

    executor = ToolExecutor(db, pro)
    result = await executor.execute(
        "get_patient_context", {"patient_id": str(other_patient.id)}
    )
    assert result == {"error": "Paciente não encontrado na sua carteira."}
    # Tool still recorded as used (it ran), but no data leaked.
    assert "get_patient_context" in executor.tools_used


async def test_search_patient_scoped_to_professional(db):
    pro = await _make_professional(db)
    other_pro = await _make_professional(db, email="other2@x.com")
    await _make_patient(db, pro, name="Ana Silva")
    await _make_patient(db, other_pro, name="Ana Outra")

    executor = ToolExecutor(db, pro)
    result = await executor.execute("search_patient_by_name", {"name": "Ana"})
    names = [p["name"] for p in result["patients"]]
    assert "Ana Silva" in names
    assert "Ana Outra" not in names  # scoped — does not leak


async def test_get_patient_context_returns_owned(db):
    pro = await _make_professional(db)
    p = await _make_patient(db, pro, name="João")

    executor = ToolExecutor(db, pro)
    result = await executor.execute("get_patient_context", {"patient_id": str(p.id)})
    assert "error" not in result
    assert result["patient_name"] == "João"
    assert "context" in result


async def test_get_inactive_patients_excludes_recent(db):
    pro = await _make_professional(db)
    inactive = await _make_patient(db, pro, name="Parado")
    active = await _make_patient(db, pro, name="Recente")
    # recent session for 'active'
    db.add(Session(
        patient_id=active.id, professional_id=pro.id,
        date=datetime.now(timezone.utc), duration=45, type="atendimento",
        objectives=[], notes="",
    ))
    await db.commit()

    executor = ToolExecutor(db, pro)
    result = await executor.execute("get_inactive_patients", {"inactive_days": 30})
    names = [p["name"] for p in result["patients"]]
    assert "Parado" in names
    assert "Recente" not in names