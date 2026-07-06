from typing import Any

from app.core.instrument_aliases import (
    CLIENT_SCORED_PROTOCOLS,
    SPM_PROTOCOL,
    has_manifest_package,
    resolve_instrument_slug,
)
from app.services.instrument_content_package import get_instrument_content_package
from app.services.instrument_scoring_service import InstrumentScoringService


def get_protocol_scoring_mode(protocol_id: str) -> str:
    pid = protocol_id.lower()
    if pid == SPM_PROTOCOL:
        return "spm"
    if pid == "abfw":
        return "battery"
    if has_manifest_package(pid):
        slug = resolve_instrument_slug(pid)
        if slug:
            try:
                package = get_instrument_content_package(slug)
                if package.archetype == "battery" and package.data.get("supports_multi_session"):
                    return "battery"
            except FileNotFoundError:
                pass
        return "manifest"
    if pid in CLIENT_SCORED_PROTOCOLS:
        return "client"
    return "manual"


def score_manifest_protocol(protocol_id: str, answers: dict[str, Any]) -> dict[str, Any]:
    slug = resolve_instrument_slug(protocol_id)
    if not slug:
        raise ValueError(f"Protocolo '{protocol_id}' não possui pacote de instrumento")
    package = get_instrument_content_package(slug)
    return InstrumentScoringService.score(package, answers)


def scores_to_assessment_fields(scores: dict[str, Any]) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []
    domains = scores.get("domains") or {}
    for key, value in domains.items():
        fields.append({"label": str(key), "value": str(value)})
    if scores.get("level_label"):
        fields.append({"label": "Nível", "value": str(scores["level_label"])})
    return fields


def scores_to_percentage(scores: dict[str, Any]) -> int:
    total = scores.get("total")
    if total is None:
        return 0
    try:
        value = float(total)
    except (TypeError, ValueError):
        return 0
    if 0 <= value <= 100:
        return int(round(value))
    if value <= 7:
        return int(round((value / 7) * 100))
    return min(100, int(round(value)))


def build_assessment_from_scores(scores: dict[str, Any]) -> dict[str, Any]:
    return {
        "result": str(scores.get("summary") or scores.get("total") or "Concluído"),
        "percentage": scores_to_percentage(scores),
        "interpretation": str(
            scores.get("interpretation") or scores.get("detail") or scores.get("summary") or ""
        ),
        "fields": scores_to_assessment_fields(scores),
    }
