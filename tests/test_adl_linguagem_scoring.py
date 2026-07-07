"""Tests for adl-linguagem ADL 2 package."""

from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.battery import BatteryResponse
from app.services.battery_report_service import export_battery_pdf
from app.services.battery_scoring_service import (
    score_adl2_module,
    synthesize_battery_scores,
)
from app.services.instrument_content_package import get_instrument_content_package


def _clear():
    get_instrument_content_package.cache_clear()


def test_adl_linguagem_package_loads():
    _clear()
    package = get_instrument_content_package("adl-linguagem")
    assert package.slug == "adl-linguagem"
    assert len(package.modules) == 3
    assert package.scoring.get("engine") == "adl2"
    lr_items = package.get_module_items("linguagem-compreensiva")
    assert len(lr_items) == 50
    assert lr_items[0]["id"] == "lr_03"


def test_adl2_raw_score_last_pass_minus_fails():
    _clear()
    package = get_instrument_content_package("adl-linguagem")
    answers = {
        "lr_03": {"response": "pass"},
        "lr_04": {"response": "fail"},
        "lr_05": {"response": "pass"},
    }
    result = score_adl2_module(
        package, "linguagem-compreensiva", answers, patient_age_months=24
    )
    assert result["raw_score"] == 4  # last pass item 5 minus 1 fail
    assert result["module_kind"] == "adl2"


def test_adl2_delay_detection():
    _clear()
    package = get_instrument_content_package("adl-linguagem")
    answers = {"lr_03": {"response": "fail"}, "lr_04": {"response": "pass"}}
    result = score_adl2_module(
        package, "linguagem-compreensiva", answers, patient_age_months=24
    )
    assert result["delay_count"] >= 1


def test_adl2_synthesize_with_norms():
    _clear()
    package = get_instrument_content_package("adl-linguagem")
    lr_answers = {f"lr_{num:02d}": {"response": "pass"} for num in range(3, 16)}
    le_answers = {f"le_{num:02d}": {"response": "pass"} for num in range(1, 12)}
    subform_scores = [
        score_adl2_module(
            package, "linguagem-compreensiva", lr_answers, patient_age_months=38
        ),
        score_adl2_module(
            package, "linguagem-expressiva", le_answers, patient_age_months=38
        ),
    ]
    synth = synthesize_battery_scores(
        package, subform_scores, patient_age_months=38
    )
    assert synth["engine"] == "adl2"
    assert synth.get("norms_applied") is True
    assert synth.get("age_band") == "36-41"
    lr = synth["domains"]["LR"]
    le = synth["domains"]["LE"]
    assert lr.get("standard_score") is not None
    assert le.get("standard_score") is not None
    assert synth.get("global_standard_score") is not None


def test_adl2_synthesize_qualitative_young_child():
    _clear()
    package = get_instrument_content_package("adl-linguagem")
    lr_answers = {f"lr_{num:02d}": {"response": "pass"} for num in range(3, 10)}
    le_answers = {f"le_{num:02d}": {"response": "pass"} for num in range(1, 15)}
    subform_scores = [
        score_adl2_module(
            package, "linguagem-compreensiva", lr_answers, patient_age_months=24
        ),
        score_adl2_module(
            package, "linguagem-expressiva", le_answers, patient_age_months=24
        ),
    ]
    assert subform_scores[1].get("norm_status") == "qualitative"
    assert subform_scores[1].get("developmental_age_band") == "24-29"

    synth = synthesize_battery_scores(
        package, subform_scores, patient_age_months=24
    )
    assert synth.get("interpretation_mode") == "qualitative"
    assert synth.get("norms_applied") is not True
    le = synth["domains"]["LE"]
    assert le.get("developmental_age_band") == "24-29"
    assert le.get("standard_score") is None


def test_adl_linguagem_pdf_export():
    _clear()
    package = get_instrument_content_package("adl-linguagem")
    now = datetime.now(timezone.utc)
    battery_fixture = BatteryResponse(
        id=str(uuid4()),
        patient_id=str(uuid4()),
        patient_name="Paciente Teste",
        professional_id=str(uuid4()),
        instrument_slug="adl-linguagem",
        instrument_title=package.instrument_title,
        status="completed",
        scores={
            "engine": "adl2",
            "setup": {
                "assessment_date": "2026-07-06",
                "examiner_name": "Dra. Camila",
                "initial_notes": "Criança colaborativa.",
            },
            "domains": {
                "LR": {
                    "title": "Linguagem Receptiva (Compreensiva)",
                    "level": "expected",
                    "raw_score": 20,
                    "standard_score": 82,
                    "delay_count": 0,
                },
                "LE": {
                    "title": "Linguagem Expressiva",
                    "level": "expected",
                    "raw_score": 18,
                    "standard_score": 80,
                    "delay_count": 0,
                },
            },
            "global_standard_score": 95,
            "clinical_conclusion": "Acompanhamento fonoaudiológico recomendado.",
            "interpretation": "ADL 2: desenvolvimento dentro do esperado.",
        },
        subforms=[],
        created_at=now,
        updated_at=now,
    )
    pdf = export_battery_pdf(battery_fixture, package)
    assert pdf[:4] == b"%PDF"
