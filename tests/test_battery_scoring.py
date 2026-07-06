"""Tests for ABFW battery scoring engines."""

from app.services.battery_scoring_service import (
    score_fluency_module,
    score_phonology_module,
    score_pragmatics_module,
    score_vocabulary_module,
    synthesize_battery_scores,
)
from app.services.instrument_content_package import get_instrument_content_package


def _package():
    return get_instrument_content_package("abfw")


def test_phonology_scoring_counts_processes():
    package = _package()
    answers = {
        "fon_im_01": {"response": "pato", "classification": "correct", "processes": []},
        "fon_im_02": {"response": "papo", "classification": "substitution", "processes": ["fronting"]},
    }
    result = score_phonology_module(
        package, "fonologia-imitacao", answers, patient_age_months=72
    )
    assert result["correct"] == 1
    assert result["altered"] == 1
    assert any(p["id"] == "fronting" for p in result["processes"])


def test_vocabulary_scoring_dvu_percentages():
    package = _package()
    items = package.get_module_items("vocabulario")[:5]
    answers = {
        items[0]["id"]: {"classification": "dvu"},
        items[1]["id"]: {"classification": "nd"},
        items[2]["id"]: {"classification": "ps"},
        items[3]["id"]: {"classification": "dvu"},
        items[4]["id"]: {"classification": "dvu"},
    }
    result = score_vocabulary_module(
        package, "vocabulario", answers, patient_age_months=48
    )
    assert result["dvu"] == 3
    assert result["total_items"] == 5
    assert result["percentage"] == 60.0


def test_fluency_scoring_calculates_rates():
    package = _package()
    answers = {
        "flu_session": {"duration_seconds": 120, "syllable_count": 200, "word_count": 80},
        "flu_syllable_repetition": {"count": 3},
        "flu_block": {"count": 1},
    }
    result = score_fluency_module(package, "fluencia", answers)
    assert result["syllables_per_minute"] == 100.0
    assert result["words_per_minute"] == 40.0
    assert result["disfluency_count"] == 4


def test_pragmatics_scoring_checklist():
    package = _package()
    items = package.get_module_items("pragmatica")[:3]
    answers = {
        items[0]["id"]: {"classification": "adequate"},
        items[1]["id"]: {"classification": "attention"},
        items[2]["id"]: {"classification": "altered"},
    }
    result = score_pragmatics_module(package, "pragmatica", answers)
    assert result["counts"]["adequate"] == 1
    assert result["counts"]["attention"] == 1
    assert result["counts"]["altered"] == 1


def test_synthesize_battery_scores():
    package = _package()
    subforms = [
        score_phonology_module(
            package,
            "fonologia-imitacao",
            {"fon_im_01": {"classification": "correct", "processes": []}},
            patient_age_months=60,
        ),
        score_vocabulary_module(
            package,
            "vocabulario",
            {"voc_animais_01": {"classification": "dvu"}},
            patient_age_months=60,
        ),
    ]
    synthesized = synthesize_battery_scores(package, subforms)
    assert "domains" in synthesized
    assert synthesized["percentage"] >= 0
