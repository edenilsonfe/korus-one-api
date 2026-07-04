from typing import Any

from app.services.spm_content_package import SpmContentPackage


def _classify_t_score(t_score: float) -> str:
    if t_score >= 70:
        return "definite"
    if t_score >= 60:
        return "some"
    return "typical"


def _classify_label(level: str) -> str:
    return {
        "typical": "Típico",
        "some": "Alguns problemas",
        "definite": "Definitivamente anormal",
    }.get(level, level)


def _domain_norms(norms: dict[str, Any], domain: str) -> tuple[float, float]:
    domain_norms = norms.get("domains", {})
    if isinstance(domain_norms, dict) and domain in domain_norms:
        entry = domain_norms[domain]
        return float(entry.get("mean", 12.0)), float(entry.get("sd", 3.0))
    return float(norms.get("mean_per_domain", 12.0)), float(norms.get("sd_per_domain", 3.0))


def compute_subform_scores(
    package: SpmContentPackage,
    subform_slug: str,
    answers: dict[str, Any],
) -> dict[str, Any]:
    subform = package.get_subform(subform_slug)
    items = package.get_items(subform_slug)
    norms = package.get_norms(subform_slug)
    scale_min, scale_max = package.get_scale_bounds()
    reverse_items = {int(item_id) for item_id in subform.get("reverse_items", [])}

    domain_scores: dict[str, dict[str, Any]] = {}
    domain_items: dict[str, list[int]] = {}

    for item in items:
        item_id = str(item["id"])
        domain = item["domain"]
        raw_value = answers.get(item_id)
        if raw_value is None:
            continue
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            continue
        value = max(scale_min, min(scale_max, value))
        if int(item["id"]) in reverse_items:
            value = (scale_min + scale_max) - value
        domain_items.setdefault(domain, []).append(value)

    total_raw = 0
    for domain, values in domain_items.items():
        raw = sum(values)
        total_raw += raw
        mean, sd = _domain_norms(norms, domain)
        if sd <= 0:
            sd = 1.0
        t_score = round(50 + 10 * (raw - mean) / sd, 1)
        level = _classify_t_score(t_score)
        domain_scores[domain] = {
            "raw": raw,
            "t_score": t_score,
            "level": level,
            "label": _classify_label(level),
            "items_answered": len(values),
        }

    if domain_scores:
        avg_t = sum(entry["t_score"] for entry in domain_scores.values()) / len(domain_scores)
        overall_level = _classify_t_score(avg_t)
    else:
        avg_t = 50.0
        overall_level = "typical"

    return {
        "subform_slug": subform_slug,
        "domains": domain_scores,
        "overall": {
            "raw_total": total_raw,
            "t_score": round(avg_t, 1),
            "level": overall_level,
            "label": _classify_label(overall_level),
        },
        "items_answered": sum(len(v) for v in domain_items.values()),
        "items_total": len(items),
    }


def synthesize_battery_scores(subform_scores: list[dict[str, Any]]) -> dict[str, Any]:
    completed = [entry for entry in subform_scores if entry.get("domains")]
    if not completed:
        return {"summary": "Nenhuma sub-forma pontuada", "subforms": subform_scores}

    flagged = []
    for entry in completed:
        slug = entry["subform_slug"]
        overall = entry.get("overall", {})
        if overall.get("level") in ("some", "definite"):
            flagged.append(f"{slug}: {overall.get('label', overall.get('level'))}")

    summary = (
        "Áreas de atenção — " + "; ".join(flagged)
        if flagged
        else "Perfil sensorial dentro da faixa típica nas sub-formas concluídas"
    )

    return {"summary": summary, "subforms": subform_scores, "engine": "spm"}


def build_clinical_report_draft(
    patient_name: str,
    subform_scores: list[dict[str, Any]],
) -> str:
    lines = [
        f"Parecer SPM — {patient_name}",
        "",
        "Síntese automática (revisão obrigatória pelo terapeuta ocupacional):",
        "",
    ]
    for entry in subform_scores:
        overall = entry.get("overall", {})
        if not overall:
            continue
        lines.append(
            f"- {entry['subform_slug']}: T={overall.get('t_score', '—')} "
            f"({overall.get('label', '—')})"
        )
    lines.extend(["", "[Revise e complemente este parecer antes de finalizar.]"])
    return "\n".join(lines)


def spm_scores_to_fields(subform_scores: list[dict[str, Any]]) -> list[dict[str, str]]:
    domain_labels = {
        "SOC": "Participação social",
        "VIS": "Visual",
        "AUD": "Auditivo",
        "TOQ": "Tato",
        "CC": "Consciência corporal",
        "EQU": "Equilíbrio e movimento",
        "PLA": "Planejamento e ideação",
    }
    fields: list[dict[str, str]] = []
    for entry in subform_scores:
        for domain_id, domain_score in (entry.get("domains") or {}).items():
            label = domain_labels.get(domain_id, domain_id)
            fields.append(
                {
                    "label": f"{entry['subform_slug']} · {label}",
                    "value": f"T={domain_score.get('t_score')} ({domain_score.get('label')})",
                }
            )
    return fields
