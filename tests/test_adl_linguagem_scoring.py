"""Tests for adl-linguagem developmental package."""

from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.battery import BatteryResponse
from app.services.battery_report_service import export_battery_pdf
from app.services.battery_scoring_service import (
    score_developmental_module,
    synthesize_battery_scores,
)
from app.services.instrument_content_package import get_instrument_content_package


def _clear():
    get_instrument_content_package.cache_clear()


def test_adl_linguagem_package_loads():
    _clear()
    package = get_instrument_content_package("adl-linguagem")
    assert package.slug == "adl-linguagem"
    assert len(package.modules) == 5
    assert package.scoring.get("engine") == "developmental_screening"


def test_adl_linguagem_delay_on_compreensao():
    _clear()
    package = get_instrument_content_package("adl-linguagem")
    answers = {"comp_01": {"response": "fail"}, "comp_02": {"response": "pass"}}
    result = score_developmental_module(
        package, "compreensao", answers, patient_age_months=24
    )
    assert result["delay_count"] >= 1
    assert result["module_kind"] == "developmental"


def test_adl_linguagem_synthesize():
    _clear()
    package = get_instrument_content_package("adl-linguagem")
    subform_scores = [
        score_developmental_module(
            package, "compreensao", {"comp_01": {"response": "fail"}}, patient_age_months=24
        )
    ]
    synth = synthesize_battery_scores(package, subform_scores)
    assert synth["engine"] == "developmental_screening"
    assert "total_delays" in synth


def test_adl_linguagem_norms_stub_applied():
    _clear()
    package = get_instrument_content_package("adl-linguagem")
    subform_scores = [
        score_developmental_module(
            package,
            "compreensao",
            {"comp_01": {"response": "pass"}, "comp_02": {"response": "pass"}},
            patient_age_months=24,
        )
    ]
    synth = synthesize_battery_scores(package, subform_scores)
    domains = synth.get("domains", {})
    comp = domains.get("COMP") or domains.get("compreensao")
    assert comp is not None
    assert comp.get("standard_score") is not None or synth.get("norms_applied")
    assert comp.get("standard_score") == 70
    assert comp.get("percentile") == 50


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
            "engine": "developmental_screening",
            "setup": {
                "assessment_date": "2026-07-06",
                "examiner_name": "Dra. Camila",
                "initial_notes": "Criança colaborativa.",
            },
            "domains": {
                "COMP": {
                    "title": "Compreensão",
                    "level": "caution",
                    "delay_count": 1,
                    "standard_score": 70,
                    "percentile": 50,
                }
            },
            "clinical_conclusion": "Acompanhamento fonoaudiológico recomendado.",
            "interpretation": "Triagem do desenvolvimento: 1 atraso(s) detectado(s).",
        },
        subforms=[],
        created_at=now,
        updated_at=now,
    )
    pdf = export_battery_pdf(battery_fixture, package)
    assert pdf[:4] == b"%PDF"
