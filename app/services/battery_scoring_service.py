"""Scoring engines for generic battery instruments (ABFW module kinds)."""

from __future__ import annotations

from typing import Any

from app.services.instrument_content_package import InstrumentContentPackage


def _patient_age_months(birth_date) -> int | None:
    if not birth_date:
        return None
    from datetime import date

    today = date.today()
    months = (today.year - birth_date.year) * 12 + (today.month - birth_date.month)
    if today.day < birth_date.day:
        months -= 1
    return max(0, months)


def _item_answer(answers: dict[str, Any], item_id: str) -> dict[str, Any]:
    raw = answers.get(item_id)
    if isinstance(raw, dict):
        return raw
    if raw is not None:
        return {"value": raw}
    return {}


def score_phonology_module(
    package: InstrumentContentPackage,
    module_slug: str,
    answers: dict[str, Any],
    *,
    patient_age_months: int | None = None,
) -> dict[str, Any]:
    items = package.get_module_items(module_slug)
    processes_catalog = {p["id"]: p for p in package.data.get("phonological_processes", [])}
    process_counts: dict[str, int] = {}
    correct = 0
    altered = 0
    item_details: list[dict[str, Any]] = []

    for item in items:
        ans = _item_answer(answers, item["id"])
        classification = ans.get("classification", "")
        response = ans.get("response", "")
        processes = ans.get("processes") or []
        if classification == "correct":
            correct += 1
        else:
            altered += 1
        for proc in processes:
            process_counts[proc] = process_counts.get(proc, 0) + 1
        item_details.append(
            {
                "id": item["id"],
                "target": item.get("target"),
                "response": response,
                "classification": classification,
                "processes": processes,
            }
        )

    process_summary = []
    for proc_id, count in sorted(process_counts.items(), key=lambda x: -x[1]):
        meta = processes_catalog.get(proc_id, {})
        expected_age = meta.get("expected_age_months")
        persistent = None
        if patient_age_months is not None and expected_age is not None:
            persistent = patient_age_months > expected_age
        process_summary.append(
            {
                "id": proc_id,
                "label": meta.get("label", proc_id),
                "count": count,
                "expected_age_months": expected_age,
                "persistent": persistent,
            }
        )

    total = len(items)
    pct = round((correct / total) * 100, 1) if total else 0.0
    return {
        "module_kind": "phonology",
        "module_slug": module_slug,
        "correct": correct,
        "altered": altered,
        "total_items": total,
        "percentage": pct,
        "processes": process_summary,
        "items": item_details,
        "summary": f"Fonologia: {correct}/{total} corretas ({pct}%)",
    }


def score_vocabulary_module(
    package: InstrumentContentPackage,
    module_slug: str,
    answers: dict[str, Any],
    *,
    patient_age_months: int | None = None,
) -> dict[str, Any]:
    items = package.get_module_items(module_slug)
    norms = package.get_norms()
    ref_by_age = norms.get("vocabulary_reference_by_age_months", {})

    categories: dict[str, dict[str, Any]] = {}
    for item in items:
        cat = item.get("category", "geral")
        if cat not in categories:
            categories[cat] = {
                "id": cat,
                "title": item.get("category_title", cat),
                "dvu": 0,
                "nd": 0,
                "ps": 0,
                "other": 0,
                "total": 0,
            }
        categories[cat]["total"] += 1
        ans = _item_answer(answers, item["id"])
        classification = ans.get("classification", "no_response")
        if classification == "dvu":
            categories[cat]["dvu"] += 1
        elif classification == "nd":
            categories[cat]["nd"] += 1
        elif classification == "ps":
            categories[cat]["ps"] += 1
        else:
            categories[cat]["other"] += 1

    ref_key = None
    if patient_age_months is not None and ref_by_age:
        age_keys = sorted(int(k) for k in ref_by_age.keys())
        for age in age_keys:
            if patient_age_months >= age:
                ref_key = str(age)
        if ref_key is None:
            ref_key = str(age_keys[0])

    category_results = []
    total_dvu = 0
    total_items = 0
    for cat in categories.values():
        pct = round((cat["dvu"] / cat["total"]) * 100, 1) if cat["total"] else 0.0
        ref_pct = None
        level = "unknown"
        if ref_key and cat["id"] in ref_by_age.get(ref_key, {}):
            ref_pct = ref_by_age[ref_key][cat["id"]]
            if pct >= ref_pct:
                level = "adequate"
            elif pct >= ref_pct * 0.7:
                level = "attention"
            else:
                level = "altered"
        total_dvu += cat["dvu"]
        total_items += cat["total"]
        category_results.append({**cat, "percentage": pct, "reference_percentage": ref_pct, "level": level})

    overall_pct = round((total_dvu / total_items) * 100, 1) if total_items else 0.0
    return {
        "module_kind": "vocabulary",
        "module_slug": module_slug,
        "dvu": total_dvu,
        "total_items": total_items,
        "percentage": overall_pct,
        "categories": category_results,
        "summary": f"Vocabulário: {total_dvu}/{total_items} DVU ({overall_pct}%)",
    }


def score_fluency_module(
    package: InstrumentContentPackage,
    module_slug: str,
    answers: dict[str, Any],
) -> dict[str, Any]:
    session = _item_answer(answers, "flu_session")
    duration_seconds = float(session.get("duration_seconds") or 0)
    syllable_count = int(session.get("syllable_count") or 0)
    word_count = int(session.get("word_count") or 0)

    disfluency_total = 0
    disfluency_breakdown: list[dict[str, Any]] = []
    for item in package.get_module_items(module_slug):
        if item.get("stimulus_type") != "counter":
            continue
        ans = _item_answer(answers, item["id"])
        count = int(ans.get("count") or 0)
        disfluency_total += count
        disfluency_breakdown.append(
            {"id": item["id"], "label": item.get("text"), "count": count, "category": item.get("category")}
        )

    minutes = duration_seconds / 60 if duration_seconds > 0 else 0
    syllables_per_min = round(syllable_count / minutes, 1) if minutes > 0 else 0
    words_per_min = round(word_count / minutes, 1) if minutes > 0 else 0
    disfluency_pct = round((disfluency_total / syllable_count) * 100, 2) if syllable_count > 0 else 0

    norms = package.get_norms().get("fluency_reference", {})
    level = "unknown"
    if syllables_per_min and norms:
        if disfluency_pct <= norms.get("disfluency_percent_max", 3):
            level = "adequate"
        elif disfluency_pct <= 5:
            level = "attention"
        else:
            level = "altered"

    return {
        "module_kind": "fluency",
        "module_slug": module_slug,
        "duration_seconds": duration_seconds,
        "syllable_count": syllable_count,
        "word_count": word_count,
        "syllables_per_minute": syllables_per_min,
        "words_per_minute": words_per_min,
        "disfluency_count": disfluency_total,
        "disfluency_percentage": disfluency_pct,
        "disfluency_breakdown": disfluency_breakdown,
        "level": level,
        "summary": f"Fluência: {syllables_per_min} síl/min, {disfluency_pct}% descontinuidade",
    }


def score_pragmatics_module(
    package: InstrumentContentPackage,
    module_slug: str,
    answers: dict[str, Any],
) -> dict[str, Any]:
    items = package.get_module_items(module_slug)
    counts = {"adequate": 0, "attention": 0, "altered": 0, "unset": 0}
    checklist: list[dict[str, Any]] = []

    for item in items:
        ans = _item_answer(answers, item["id"])
        level = ans.get("classification") or ans.get("level") or "unset"
        if level not in counts:
            level = "unset"
        counts[level] += 1
        checklist.append(
            {
                "id": item["id"],
                "text": item.get("text"),
                "category": item.get("category"),
                "level": level,
                "notes": ans.get("notes", ""),
            }
        )

    total = len(items)
    adequate_pct = round((counts["adequate"] / total) * 100, 1) if total else 0.0
    return {
        "module_kind": "pragmatics",
        "module_slug": module_slug,
        "counts": counts,
        "checklist": checklist,
        "percentage": adequate_pct,
        "summary": f"Pragmática: {counts['adequate']}/{total} itens adequados",
    }


def score_battery_subform(
    package: InstrumentContentPackage,
    module_slug: str,
    answers: dict[str, Any],
    *,
    patient_age_months: int | None = None,
) -> dict[str, Any]:
    mod = package.get_module_config(module_slug)
    kind = mod.get("module_kind", "generic")
    dispatch = {
        "phonology": score_phonology_module,
        "vocabulary": score_vocabulary_module,
        "fluency": score_fluency_module,
        "pragmatics": score_pragmatics_module,
    }
    handler = dispatch.get(kind)
    if not handler:
        total = len(answers)
        return {"module_kind": kind, "module_slug": module_slug, "total_items": total, "summary": "Concluído"}
    if kind in ("phonology", "vocabulary"):
        return handler(package, module_slug, answers, patient_age_months=patient_age_months)
    return handler(package, module_slug, answers)


def synthesize_battery_scores(
    package: InstrumentContentPackage,
    subform_scores: list[dict[str, Any]],
) -> dict[str, Any]:
    domains: dict[str, Any] = {}
    percentages: list[float] = []
    critical_items: list[dict[str, Any]] = []

    domain_groups: dict[str, list[dict[str, Any]]] = {}
    for score in subform_scores:
        mod = package.get_module_config(score["module_slug"])
        domain_id = mod.get("domain", score["module_slug"])
        domain_groups.setdefault(domain_id, []).append(score)

    for domain_id, group in domain_groups.items():
        if len(group) == 1:
            domains[domain_id] = group[0]
        else:
            pcts = [float(s["percentage"]) for s in group if "percentage" in s]
            merged_pct = round(sum(pcts) / len(pcts), 1) if pcts else 0.0
            domains[domain_id] = {
                "module_kind": group[0].get("module_kind"),
                "module_slug": domain_id,
                "submodules": group,
                "percentage": merged_pct,
                "summary": " · ".join(s.get("summary", "") for s in group),
            }

    for score in subform_scores:
        mod = package.get_module_config(score["module_slug"])
        domain_id = mod.get("domain", score["module_slug"])
        domain_score = domains.get(domain_id, score)
        if "percentage" in score:
            percentages.append(float(score["percentage"]))

        if score.get("module_kind") == "vocabulary":
            vocab = domain_score if domain_score.get("module_kind") == "vocabulary" else score
            for cat in vocab.get("categories", []):
                if cat.get("level") == "altered":
                    critical_items.append(
                        {
                            "type": "category",
                            "label": cat.get("title"),
                            "detail": f"{cat.get('percentage')}% DVU (ref. {cat.get('reference_percentage')}%)",
                        }
                    )
        if score.get("module_kind") == "phonology":
            phon = score
            for proc in phon.get("processes", []):
                if proc.get("persistent"):
                    critical_items.append(
                        {
                            "type": "process",
                            "label": proc.get("label"),
                            "detail": f"{proc.get('count')} ocorrências — persistente para idade",
                        }
                    )

    overall = round(sum(percentages) / len(percentages), 1) if percentages else 0.0
    return {
        "engine": "battery_module_kind",
        "domains": domains,
        "subforms": subform_scores,
        "total": overall,
        "percentage": overall,
        "critical_items": critical_items,
        "summary": f"ABFW — desempenho geral {overall}%",
        "interpretation": (
            f"Desempenho agregado de {overall}% nos módulos aplicados. "
            "Correlacionar achados com avaliação clínica completa."
        ),
    }


def battery_scores_to_fields(scores: dict[str, Any]) -> list[dict[str, str]]:
    fields: list[dict[str, str]] = []
    for slug, domain_score in (scores.get("domains") or {}).items():
        if isinstance(domain_score, dict):
            fields.append({"label": slug, "value": domain_score.get("summary", str(domain_score))})
    fields.append({"label": "Geral", "value": f"{scores.get('percentage', 0)}%"})
    return fields
