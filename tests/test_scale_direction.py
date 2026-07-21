"""Tests for observational scale_direction (lower_is_better inversion)."""

from app.services.battery_scoring_service import score_observational_module
from app.services.instrument_content_package import (
    clear_instrument_content_package_cache,
    get_instrument_content_package,
)


def _clear_cache():
    clear_instrument_content_package_cache()


def test_mbgr_lower_is_better_inverts_severe_scores():
    _clear_cache()
    package = get_instrument_content_package("mbgr")
    items = package.get_module_items("face")[:2]
    answers = {
        items[0]["id"]: {"value": 3},
        items[1]["id"]: {"value": 3},
    }
    result = score_observational_module(package, "face", answers)
    assert result["scale_direction"] == "lower_is_better"
    assert result["percentage"] == 0.0
    assert result["level"] == "altered"


def test_mbgr_lower_is_better_rewards_low_scores():
    _clear_cache()
    package = get_instrument_content_package("mbgr")
    items = package.get_module_items("face")[:2]
    answers = {
        items[0]["id"]: {"value": 0},
        items[1]["id"]: {"value": 1},
    }
    result = score_observational_module(package, "face", answers)
    assert result["percentage"] == 83.3
    assert result["level"] == "expected"


def test_pard_consistency_lower_is_better():
    _clear_cache()
    package = get_instrument_content_package("pard")
    items = package.get_module_items("liquido-fino")[:2]
    answers = {
        items[0]["id"]: {"value": 0},
        items[1]["id"]: {"value": 0},
    }
    good = score_observational_module(package, "liquido-fino", answers)
    assert good["percentage"] == 100.0

    answers_bad = {
        items[0]["id"]: {"value": 3},
        items[1]["id"]: {"value": 3},
    }
    bad = score_observational_module(package, "liquido-fino", answers_bad)
    assert bad["percentage"] == 0.0
    assert bad["level"] == "altered"
