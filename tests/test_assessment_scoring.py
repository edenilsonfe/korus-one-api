"""Tests for assessment scoring helpers and protocol modes."""

import pytest

from app.core.instrument_aliases import (
    CLIENT_SCORED_PROTOCOLS,
    SPM_PROTOCOL,
    get_protocol_scoring_mode,
    has_manifest_package,
    resolve_instrument_slug,
)
from app.services.assessment_scoring import (
    build_assessment_from_scores,
    score_manifest_protocol,
    scores_to_percentage,
)


@pytest.mark.parametrize(
    ("protocol_id", "expected_mode"),
    [
        ("spm", "spm"),
        ("fois", "manifest"),
        ("m-chat", "client"),
        ("entrevista-aprendizagem", "client"),
    ],
)
def test_get_protocol_scoring_mode(protocol_id: str, expected_mode: str):
    assert get_protocol_scoring_mode(protocol_id) == expected_mode


def test_resolve_instrument_slug_aliases():
    assert resolve_instrument_slug("ados2") == "ados-2"
    assert resolve_instrument_slug("vb-mapp") == "vb-mapp"


def test_has_manifest_package():
    assert has_manifest_package("fois") is True
    assert has_manifest_package("m-chat") is False


def test_client_scored_protocols_contains_rastreios():
    assert "m-chat" in CLIENT_SCORED_PROTOCOLS
    assert "portage" in CLIENT_SCORED_PROTOCOLS


def test_score_manifest_fois():
    scores = score_manifest_protocol("fois", {"fois_level": 5})
    assert scores["engine"] == "scaled_sum"
    assert scores["total"] == 5


def test_build_assessment_from_scores():
    derived = build_assessment_from_scores(
        {"summary": "Risco moderado", "total": 65, "domains": {"A": "ok"}}
    )
    assert derived["result"] == "Risco moderado"
    assert derived["percentage"] == 65
    assert len(derived["fields"]) >= 1


@pytest.mark.parametrize(
    ("total", "expected"),
    [(65, 65), (4, 57), ("invalid", 0)],
)
def test_scores_to_percentage(total, expected):
    assert scores_to_percentage({"total": total}) == expected


def test_spm_protocol_constant():
    assert SPM_PROTOCOL == "spm"
