"""Summarize Brazilian norms availability for scoring metadata and UI."""

from __future__ import annotations

from typing import Any

from app.services.instrument_content_package import InstrumentContentPackage

LEVEL_LABELS: dict[str, str] = {
    "official": "Normas BR oficiais",
    "partial": "Normas BR parciais",
    "qualitative": "Interpretação qualitativa (manual)",
    "reference": "Referência científica",
    "public_reference": "Referência pública (aproximada)",
    "not_applicable": "Sem norma populacional",
    "stub": "Normas BR pendentes",
    "unknown": "Status normativo indefinido",
}

LEVEL_DETAILS: dict[str, str] = {
    "official": "Escores padronizados conforme tabelas licenciadas do editor.",
    "partial": "Parte das faixas etárias possui tabelas oficiais; demais usam escore bruto.",
    "qualitative": "Faixa etária abaixo de 3 anos — idade de desenvolvimento por habilidades (sem EP).",
    "reference": "Interpretação baseada em estudos publicados — não substitui manual do editor.",
    "public_reference": "Referência etária aproximada para heatmap — não substitui norma licenciada.",
    "not_applicable": "Instrumento critério-referenciado ou ordinal — interpretação clínica direta.",
    "stub": "Exibir apenas pontuação bruta até publicação de normas brasileiras licenciadas.",
    "unknown": "Verifique o pacote do instrumento antes de interpretar escores padronizados.",
}

CRITERION_ENGINES = frozenset({"domain_mastery"})
NORMATIVE_ENGINES = frozenset(
    {"adl2", "developmental_screening", "scaled_sum", "scaled_likert_mean", "battery_module"}
)


def _collect_norm_statuses(norms: dict[str, Any]) -> set[str]:
    statuses: set[str] = set()
    root = norms.get("status")
    if root:
        statuses.add(str(root))

    for domain in (norms.get("domains") or {}).values():
        if not isinstance(domain, dict):
            continue
        if domain.get("status"):
            statuses.add(str(domain["status"]))
        for band in (domain.get("by_age_band") or {}).values():
            if isinstance(band, dict) and band.get("status"):
                statuses.add(str(band["status"]))

    global_language = norms.get("global_language") or {}
    for band in (global_language.get("by_age_band") or {}).values():
        if isinstance(band, dict) and band.get("status"):
            statuses.add(str(band["status"]))

    return statuses


def _resolve_level(
    statuses: set[str],
    *,
    engine: str | None,
    norms: dict[str, Any],
) -> str:
    if engine in CRITERION_ENGINES:
        return "not_applicable"

    root = str(norms.get("status") or "").lower()
    if root == "reference" and norms.get("reference_max"):
        return "reference"
    if root == "public_reference":
        return "public_reference"

    normalized = {s.lower() for s in statuses}
    if not normalized:
        return "stub" if engine in NORMATIVE_ENGINES else "not_applicable"

    if normalized <= {"not_applicable", "n/a"}:
        return "not_applicable"

    if "official" in normalized or "licensed" in normalized:
        if "stub" in normalized or "approx" in normalized:
            return "partial"
        if "qualitative" in normalized:
            return "partial"
        return "official"

    if "qualitative" in normalized:
        if "official" in normalized or "licensed" in normalized:
            return "partial"
        return "qualitative"

    if "reference" in normalized:
        return "reference"
    if "public_reference" in normalized:
        return "public_reference"
    if "stub" in normalized:
        return "stub"

    return "unknown"


def summarize_norms_status(
    package: InstrumentContentPackage,
    *,
    domain_entries: dict[str, Any] | None = None,
    norms_applied: bool | None = None,
) -> dict[str, Any]:
    norms = package.get_norms()
    engine = package.scoring.get("engine")
    note = str(norms.get("note") or "").strip()

    statuses = _collect_norm_statuses(norms)
    session_statuses: set[str] = set()
    if domain_entries:
        for entry in domain_entries.values():
            if isinstance(entry, dict) and entry.get("norm_status"):
                session_statuses.add(str(entry["norm_status"]))

    if session_statuses:
        statuses |= session_statuses

    level = _resolve_level(statuses, engine=engine, norms=norms)

    if norms_applied is False and level in ("official", "partial"):
        if session_statuses and session_statuses <= {"stub"}:
            level = "stub"
        elif level == "partial":
            level = "partial"
        else:
            level = "stub"

    if norms_applied is True and level == "stub":
        level = "partial"

    show_standard = level in ("official", "partial", "reference")
    if level in ("stub", "qualitative"):
        show_standard = False

    detail = note or LEVEL_DETAILS.get(level, LEVEL_DETAILS["unknown"])
    source = norms.get("source")

    return {
        "level": level,
        "label": LEVEL_LABELS.get(level, LEVEL_LABELS["unknown"]),
        "detail": detail,
        "show_standard_scores": show_standard,
        "source": source,
    }


def attach_norms_status(
    scores: dict[str, Any],
    package: InstrumentContentPackage,
) -> dict[str, Any]:
    domain_entries = scores.get("domains")
    domains = domain_entries if isinstance(domain_entries, dict) else None
    norms_applied = scores.get("norms_applied")
    if norms_applied is not None:
        norms_applied = bool(norms_applied)
    scores["norms_status"] = summarize_norms_status(
        package,
        domain_entries=domains,
        norms_applied=norms_applied,
    )
    return scores
