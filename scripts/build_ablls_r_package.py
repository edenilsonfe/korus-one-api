#!/usr/bin/env python3
"""Build ABLLS-R manifest + items from translated protocol extract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "app" / "data" / "ablls-r"
ITEMS_DIR = DATA / "items"
EXTRACT = (
    ROOT.parent / "korus-one-web" / "scripts" / "ablls-r-pdf-extract.txt"
)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ablls_r_item_catalog import (  # noqa: E402
    DOMAIN_ORDER,
    DOMAIN_TASK_COUNTS,
    DOMAIN_TITLES,
    MANUAL_ITEMS,
    SKIP_TASK_NAME_MARKERS,
)

TASK_MARKER = re.compile(r"^([A-Z])\s*(\d+)\s*$")
SCALE_ROW = re.compile(r"^0(\s+1(\s+2(\s+3(\s+4)?)?)?)?\s*$")
HEADER_ROW = re.compile(
    r"^Tarefa\s+Resultado\s+Nome",
    re.I,
)
CRITERION_ROW = re.compile(r"^[0-4]=\s*")


def _normalize_task_id(domain: str, number: int) -> str:
    return f"{domain}{number}"


def _strip_noise(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    for line in lines:
        s = line.strip()
        if not s:
            continue
        if SCALE_ROW.match(s.replace("     ", " ")):
            continue
        if HEADER_ROW.search(s):
            continue
        if s in {",", "Inserir", "desenho"}:
            continue
        cleaned.append(s)
    return cleaned


def _split_block(lines: list[str]) -> dict[str, str]:
    """Heuristic split of PDF block into protocol fields."""
    if not lines:
        return {
            "task_name": "",
            "objective": "",
            "question": "",
            "example": "",
            "criteria": "",
            "notes": "",
        }

    criteria_lines: list[str] = []
    body: list[str] = []
    for line in lines:
        if CRITERION_ROW.match(line) or line.startswith("Nota:"):
            criteria_lines.append(line)
        else:
            body.append(line)

    # Task name: first 1–3 short lines before a long objective line.
    name_parts: list[str] = []
    idx = 0
    while idx < len(body) and len(name_parts) < 4:
        line = body[idx]
        if len(line) > 90 and name_parts:
            break
        name_parts.append(line)
        idx += 1
        if len(" ".join(name_parts)) > 70 and idx < len(body) and len(body[idx]) > 90:
            break

    remainder = body[idx:]
    objective = ""
    question = ""
    example = ""
    notes = ""

    if remainder:
        # Find question line (often ends with ?)
        q_idx = next((i for i, ln in enumerate(remainder) if "?" in ln), None)
        if q_idx is not None:
            objective = " ".join(remainder[:q_idx]).strip()
            question = remainder[q_idx].strip()
            after_q = remainder[q_idx + 1 :]
            if after_q:
                # Example often before criteria-like short lines
                ex_end = len(after_q)
                for i, ln in enumerate(after_q):
                    if CRITERION_ROW.match(ln):
                        ex_end = i
                        break
                example = " ".join(after_q[:ex_end]).strip()
                extra_notes = [ln for ln in after_q[ex_end:] if ln.startswith("Nota:")]
                if extra_notes:
                    notes = " ".join(extra_notes)
        else:
            objective = " ".join(remainder).strip()

    criteria = "\n".join(criteria_lines)
    note_inline = [ln for ln in lines if ln.startswith("Nota:") or ln.startswith("Apêndice")]
    if note_inline and not notes:
        notes = " ".join(note_inline)

    return {
        "task_name": " ".join(name_parts).strip(),
        "objective": objective,
        "question": question,
        "example": example,
        "criteria": criteria,
        "notes": notes,
    }


def parse_extract(text: str) -> dict[str, dict[str, str]]:
    lines = text.splitlines()
    markers: list[tuple[int, str, int]] = []
    for i, line in enumerate(lines):
        m = TASK_MARKER.match(line.strip())
        if m:
            markers.append((i, m.group(1), int(m.group(2))))

    parsed: dict[str, dict[str, str]] = {}
    for idx, (start, domain, number) in enumerate(markers):
        end = markers[idx + 1][0] if idx + 1 < len(markers) else len(lines)
        block_lines = _strip_noise([ln.strip() for ln in lines[start + 1 : end]])
        fields = _split_block(block_lines)
        task_id = _normalize_task_id(domain, number)
        fields["domain"] = domain
        fields["task_number"] = str(number)
        parsed[task_id] = fields
    return parsed


def _format_item_text(task_id: str, fields: dict[str, str]) -> str:
    parts = [f"{task_id} — {fields.get('task_name') or 'Tarefa'}"]
    for label, key in (
        ("Objetivo", "objective"),
        ("Pergunta", "question"),
        ("Exemplo", "example"),
        ("Critérios", "criteria"),
        ("Notas", "notes"),
    ):
        value = (fields.get(key) or "").strip()
        if value:
            parts.append(f"{label}: {value}")
    return "\n\n".join(parts)


def _item_record(task_id: str, fields: dict[str, str]) -> dict:
    domain = fields["domain"]
    return {
        "id": task_id,
        "domain": domain,
        "module": domain,
        "text": _format_item_text(task_id, fields),
        "task_name": fields.get("task_name", ""),
        "objective": fields.get("objective", ""),
        "question": fields.get("question", ""),
        "example": fields.get("example", ""),
        "criteria": fields.get("criteria", ""),
        "notes": fields.get("notes", ""),
    }


def _apply_fixes(raw: dict[str, dict[str, str]]) -> dict[str, dict[str, str]]:
    items = dict(raw)

    # Drop non-official J20 (Brazilian adjective agreement insert).
    j20 = items.get("J20")
    if j20:
        name = (j20.get("task_name") or "").lower()
        if any(marker in name for marker in SKIP_TASK_NAME_MARKERS):
            del items["J20"]

    # Official J20 content was labeled J21 in the PDF.
    if "J21" in items:
        j21 = items.pop("J21")
        j21["task_number"] = "20"
        items["J20"] = j21

    # Add missing M11/M12 from catalog.
    for task_id, fields in MANUAL_ITEMS.items():
        domain = task_id[0]
        items[task_id] = {
            **fields,
            "domain": domain,
            "task_number": task_id[1:],
        }

    return items


def _sort_key(task_id: str) -> tuple[str, int]:
    m = re.match(r"^([A-Z])(\d+)$", task_id)
    if not m:
        return ("", 0)
    return (m.group(1), int(m.group(2)))


def build_items(raw: dict[str, dict[str, str]]) -> list[dict]:
    fixed = _apply_fixes(raw)
    ordered_ids = sorted(fixed.keys(), key=_sort_key)
    return [_item_record(task_id, fixed[task_id]) for task_id in ordered_ids]


def build_manifest(items: list[dict]) -> dict:
    domains = [{"id": d, "title": f"{d} — {DOMAIN_TITLES[d]}"} for d in DOMAIN_ORDER]

    modules: dict[str, dict] = {}
    scoring_domains: dict[str, dict] = {}

    for domain in DOMAIN_ORDER:
        domain_items = [it for it in items if it["domain"] == domain]
        domain_items.sort(key=lambda it: _sort_key(it["id"]))
        rel_path = f"items/{domain}.json"
        modules[domain] = {
            "id": domain,
            "title": f"{domain} — {DOMAIN_TITLES[domain]}",
            "domain": domain,
            "items_file": rel_path,
            "item_count": len(domain_items),
        }
        scoring_domains[domain] = {
            "method": "mastery_pct",
            "item_ids": [it["id"] for it in domain_items],
        }

    return {
        "version": 2,
        "package_id": "ablls-r-br-v1",
        "instrument_slug": "ablls-r",
        "instrument_title": "ABLLS-R — Avaliação de Habilidades Básicas de Linguagem e Aprendizagem",
        "publisher": "Tradução pt-BR (protocolo Partington 2006; uso clínico requer licença oficial)",
        "license_ref": "PARTINGTON-ABLLS-R-STRUCTURE",
        "content_status": "official-structure",
        "norms_region": "BR",
        "norms_file": "norms-br.json",
        "archetype": "multi_domain",
        "supports_multi_session": True,
        "scale": [
            {"value": 0, "label": "Não adquirido (0)"},
            {"value": 1, "label": "Emergente / parcial (1)"},
            {"value": 2, "label": "Adquirido (≥2 no protocolo)"},
        ],
        "domains": domains,
        "items_file": "items/all.json",
        "modules": modules,
        "scoring": {
            "engine": "domain_mastery",
            "domains": scoring_domains,
            "interpretations": [
                {
                    "min": 0,
                    "max": 49,
                    "label": "Habilidades iniciais — foco em ensino estruturado",
                },
                {
                    "min": 50,
                    "max": 79,
                    "label": "Desenvolvimento parcial — metas intermediárias",
                },
                {
                    "min": 80,
                    "max": 100,
                    "label": "Domínio elevado na amostra aplicada",
                },
            ],
        },
        "report": {
            "template_id": "ablls-r-br-v1",
            "sections": [
                "identificacao",
                "resultados",
                "interpretacao",
                "recomendacoes",
                "metas",
            ],
        },
        "informant_forms": [],
        "suggested_goals_template": True,
    }


def _validate(items: list[dict]) -> None:
    by_domain: dict[str, list[str]] = {}
    for it in items:
        by_domain.setdefault(it["domain"], []).append(it["id"])

    total = len(items)
    expected = sum(DOMAIN_TASK_COUNTS.values())
    if total != expected:
        details = {
            d: (len(by_domain.get(d, [])), DOMAIN_TASK_COUNTS[d])
            for d in DOMAIN_ORDER
            if len(by_domain.get(d, [])) != DOMAIN_TASK_COUNTS[d]
        }
        raise SystemExit(
            f"Task count mismatch: got {total}, expected {expected}. Domains: {details}"
        )


def main() -> None:
    if not EXTRACT.is_file():
        raise SystemExit(f"Extract not found: {EXTRACT}")

    text = EXTRACT.read_text(encoding="utf-8")
    raw = parse_extract(text)
    items = build_items(raw)
    _validate(items)

    ITEMS_DIR.mkdir(parents=True, exist_ok=True)

    by_domain: dict[str, list[dict]] = {}
    for it in items:
        by_domain.setdefault(it["domain"], []).append(it)

    for domain, domain_items in by_domain.items():
        path = ITEMS_DIR / f"{domain}.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(domain_items, handle, ensure_ascii=False, indent=2)
            handle.write("\n")

    all_path = ITEMS_DIR / "all.json"
    with all_path.open("w", encoding="utf-8") as handle:
        json.dump(items, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    manifest = build_manifest(items)
    manifest_path = DATA / "manifest.json"
    with manifest_path.open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    norms = {
        "version": 1,
        "region": "BR",
        "status": "stub",
        "note": (
            "ABLLS-R é critério-referenciado (Partington 2006). "
            "Normas BR não publicadas — scoring por % de mestria por domínio."
        ),
        "domains": {},
        "age_bands": [],
    }
    with (DATA / "norms-br.json").open("w", encoding="utf-8") as handle:
        json.dump(norms, handle, ensure_ascii=False, indent=2)
        handle.write("\n")

    print(f"Wrote {len(items)} items across {len(by_domain)} domains -> {DATA}")


if __name__ == "__main__":
    main()
