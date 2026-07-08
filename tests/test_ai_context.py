"""Tests for rich AI clinical context builders."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from app.services.ai_context import (
    ANAMNESIS_MAX_CHARS,
    EVOLUTION_CONTENT_MAX_CHARS,
    _summarize_scores,
    build_context,
)


def test_summarize_scores_tolerant_formats():
    scores = {
        "domains": {
            "receptivo": {
                "title": "Linguagem receptiva",
                "level": "abaixo",
                "percentage": 55,
                "standard_score": 85,
                "percentile": 16,
            },
            "bad": "ignored",
        },
        "categories": {
            "fono": {"title": "Fonologia", "percentage": 70},
        },
    }
    text = _summarize_scores(scores)
    assert "Linguagem receptiva" in text
    assert "EP 85" in text
    assert "P16" in text
    assert "Fonologia" in text


def test_summarize_scores_empty():
    assert _summarize_scores(None) == ""
    assert _summarize_scores({}) == ""


@pytest.mark.asyncio
async def test_build_context_omits_empty_sections(monkeypatch):
    import app.services.ai_context as ctx

    async def fake_identity(_db, _patient_id, **_kwargs):
        return "Nome: João"

    async def fake_anamnesis(_db, _patient_id, **_kwargs):
        return ""

    monkeypatch.setattr(ctx, "build_identity_section", fake_identity)
    monkeypatch.setattr(ctx, "build_anamnesis_section", fake_anamnesis)
    monkeypatch.setitem(ctx._SECTION_BUILDERS, "identity", "build_identity_section")
    monkeypatch.setitem(ctx._SECTION_BUILDERS, "anamnesis", "build_anamnesis_section")

    db = AsyncMock()
    text = await build_context(db, uuid4(), ["identity", "anamnesis"], max_chars=12000)
    assert "### Identificação" in text
    assert "### Anamnese" not in text
    assert "N/A" not in text


@pytest.mark.asyncio
async def test_build_context_truncates_last_sections(monkeypatch):
    import app.services.ai_context as ctx

    async def fake_identity(_db, _patient_id, **_kwargs):
        return "x" * 200

    async def fake_evolutions(_db, _patient_id, **_kwargs):
        return "y" * 500

    monkeypatch.setattr(ctx, "build_identity_section", fake_identity)
    monkeypatch.setattr(ctx, "build_evolutions_section", fake_evolutions)
    monkeypatch.setitem(ctx._SECTION_BUILDERS, "identity", "build_identity_section")
    monkeypatch.setitem(ctx._SECTION_BUILDERS, "evolutions", "build_evolutions_section")

    db = AsyncMock()
    text = await build_context(db, uuid4(), ["identity", "evolutions"], max_chars=280)
    assert "### Identificação" in text
    assert len(text) <= 320


def test_anamnesis_char_limit_constant():
    assert ANAMNESIS_MAX_CHARS == 2000


def test_evolution_content_char_limit_constant():
    assert EVOLUTION_CONTENT_MAX_CHARS == 1500

