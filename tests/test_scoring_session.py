"""C2 ScoringSession — NormalizedScores behind a small interface (manifest slice)."""

from __future__ import annotations

import pytest

from app.services.scoring_session import NormalizedScores, ScoringSession, ScoreError


def test_from_protocol_manifest_fois_scores_answers():
    session = ScoringSession.from_protocol("fois", "manifest")
    result = session.score({"fois_level": 5})
    assert isinstance(result, NormalizedScores)
    assert result.percentage == 71  # FOIS total 5 → round(5/7*100)
    assert result.interpretation  # non-empty from engine
    assert result.raw_scores["engine"] == "scaled_sum"
    assert result.raw_scores["total"] == 5
    assert result.norms is None or isinstance(result.norms, dict)


def test_to_assessment_fields_matches_build_shape():
    session = ScoringSession.from_protocol("fois", "manifest")
    result = session.score({"fois_level": 5})
    fields = result.to_assessment_fields()
    assert isinstance(fields, list)
    assert all("label" in f and "value" in f for f in fields)


def test_score_from_precomputed_scores_fixture_adapter():
    """Second adapter: precomputed scores dict (no engine) → NormalizedScores."""
    session = ScoringSession.from_scores(
        {"summary": "Risco moderado", "total": 65, "domains": {"A": "ok"}, "interpretation": "Atenção"}
    )
    result = session.score({})  # answers ignored when scores pre-bound
    assert result.percentage == 65
    assert result.result == "Risco moderado"
    assert result.interpretation == "Atenção"
    assert len(result.to_assessment_fields()) >= 1


def test_unsupported_mode_raises_score_error():
    with pytest.raises(ScoreError):
        ScoringSession.from_protocol("snap-iv", "client").score({})


def test_unknown_manifest_package_raises():
    with pytest.raises(ScoreError):
        ScoringSession.from_protocol("nao-existe-xyz", "manifest").score({"x": 1})
