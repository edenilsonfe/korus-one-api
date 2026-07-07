from app.services.instrument_content_package import InstrumentContentPackage
from app.services.norms_status import summarize_norms_status


def test_ablls_r_not_applicable():
    package = InstrumentContentPackage(
        "ablls-r",
        {
            "norms_file": "norms-br.json",
            "scoring": {"engine": "domain_mastery"},
            "norms": {
                "status": "stub",
                "note": "ABLLS-R é critério-referenciado.",
            },
        },
    )
    status = summarize_norms_status(package)
    assert status["level"] == "not_applicable"
    assert status["show_standard_scores"] is False


def test_adl2_partial_from_mixed_bands():
    package = InstrumentContentPackage(
        "adl-linguagem",
        {
            "content_status": "partial-norms",
            "scoring": {"engine": "adl2"},
            "norms": {
                "domains": {
                    "LR": {
                        "by_age_band": {
                            "36-41": {"status": "official", "raw_to_standard": []},
                            "12-17": {"status": "qualitative", "raw_to_standard": []},
                        }
                    }
                }
            },
        },
    )
    status = summarize_norms_status(package)
    assert status["level"] == "partial"


def test_amiofe_reference():
    package = InstrumentContentPackage(
        "amiofe",
        {
            "scoring": {"engine": "observational_domains"},
            "norms": {
                "status": "reference",
                "reference_max": 103,
                "note": "ETAMIOFE Felício et al.",
            },
        },
    )
    status = summarize_norms_status(package)
    assert status["level"] == "reference"
    assert status["show_standard_scores"] is True


def test_adl2_partial_qualitative_and_official():
    package = InstrumentContentPackage(
        "adl-linguagem",
        {
            "content_status": "partial-norms",
            "scoring": {"engine": "adl2"},
            "norms": {
                "qualitative_age_bands": ["12-17", "18-23", "24-29", "30-35"],
                "domains": {
                    "LR": {
                        "by_age_band": {
                            "12-17": {"status": "qualitative"},
                            "36-41": {"status": "official", "raw_to_standard": []},
                        }
                    }
                },
            },
        },
    )
    status = summarize_norms_status(package)
    assert status["level"] == "partial"


def test_session_stub_overrides_when_norms_not_applied():
    package = InstrumentContentPackage(
        "adl-linguagem",
        {"scoring": {"engine": "adl2"}, "norms": {"domains": {"LR": {"by_age_band": {"36-41": {"status": "official"}}}}}},
    )
    status = summarize_norms_status(
        package,
        domain_entries={"LR": {"norm_status": "stub"}},
        norms_applied=False,
    )
    assert status["level"] == "stub"
