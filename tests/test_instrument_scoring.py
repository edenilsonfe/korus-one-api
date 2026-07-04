"""Tests for instrument scoring engines."""

import pytest

from app.services.instrument_content_package import get_instrument_content_package
from app.services.instrument_scoring_service import InstrumentScoringService


@pytest.fixture(autouse=True)
def clear_package_cache():
    get_instrument_content_package.cache_clear()
    yield
    get_instrument_content_package.cache_clear()


def test_fois_scaled_sum():
    package = get_instrument_content_package("fois")
    scores = InstrumentScoringService.score(package, {"fois_level": 4})
    assert scores["engine"] == "scaled_sum"
    assert scores["total"] == 4
    assert "FOIS" in scores["summary"]


def test_pard_risk_cutoff():
    package = get_instrument_content_package("pard")
    answers = {f"pard_{i:02d}": 1 for i in range(1, 4)}
    scores = InstrumentScoringService.score(package, answers)
    assert scores["total"] == 3
    assert scores["interpretation"] is not None


def test_vb_mapp_domain_mastery():
    package = get_instrument_content_package("vb-mapp")
    domain_config = package.scoring["domains"]["LING"]
    item_ids = domain_config["item_ids"][:3]
    answers = {item_id: 2 for item_id in item_ids}
    scores = InstrumentScoringService.score(package, answers)
    assert scores["engine"] == "domain_mastery"
    assert "LING" in scores["domains"]


def test_spm_subform_scoring():
    from app.services.spm_content_package import get_spm_content_package
    from app.services.spm_scoring_service import compute_subform_scores, synthesize_battery_scores

    get_spm_content_package.cache_clear()
    package = get_spm_content_package()
    subforms = package.list_subforms()
    clinical = next(s for s in subforms if s["filler"] == "clinical" and s["item_count"] > 0)
    items = package.get_items(clinical["slug"])[:5]
    answers = {str(item["id"]): 2 for item in items}
    scores = compute_subform_scores(package, clinical["slug"], answers)
    assert scores["subform_slug"] == clinical["slug"]
    assert "overall" in scores
    battery = synthesize_battery_scores([scores])
    assert "summary" in battery
