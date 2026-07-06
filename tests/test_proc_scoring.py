"""Tests for PROC observational battery scoring."""

from app.services.battery_scoring_service import (
    score_observational_module,
    synthesize_battery_scores,
)
from app.services.instrument_content_package import get_instrument_content_package


def _package():
    return get_instrument_content_package("proc")


def test_observational_scoring_excludes_not_observed_from_denominator():
    package = _package()
    items = package.get_module_items("formas-comunicacao")[:4]
    answers = {
        items[0]["id"]: {"value": 2},
        items[1]["id"]: {"value": 1},
        items[2]["id"]: {"value": 0},
        items[3]["id"]: {"value": 2},
    }
    result = score_observational_module(package, "formas-comunicacao", answers)
    assert result["not_observed"] == 1
    assert result["percentage"] == 83.3
    assert result["level"] in ("expected", "attention", "altered")


def test_observational_unanswered_not_penalized():
    package = _package()
    items = package.get_module_items("imitacao")[:3]
    answers = {
        items[0]["id"]: {"value": 2},
        items[1]["id"]: {"value": 2},
    }
    result = score_observational_module(package, "imitacao", answers)
    assert result["unanswered"] >= 1
    assert result["percentage"] == 100.0


def test_observational_checklist_module():
    package = _package()
    answers = {
        "fcom_checklist": {
            "selected": ["instrumental", "interativa", "nomeacao", "jogo"],
            "notes": "Observado durante brincadeira livre.",
        }
    }
    result = score_observational_module(package, "funcoes-comunicativas", answers)
    assert result["module_kind"] == "observational"
    assert result["percentage"] > 0


def test_synthesize_proc_battery_scores():
    package = _package()
    subforms = [
        score_observational_module(
            package,
            "formas-comunicacao",
            {"fc_gestos_convencionais": {"value": 2}, "fc_vocalizacoes": {"value": 1}},
        ),
        score_observational_module(
            package,
            "imitacao",
            {"im_gestual": {"value": 2}},
        ),
    ]
    synthesized = synthesize_battery_scores(package, subforms)
    assert synthesized["engine"] == "observational_domains"
    assert "domains" in synthesized
    assert synthesized["percentage"] >= 0
    assert "strengths" in synthesized
