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
    r"^Tarefa\s+Resultado\s+Nome|Tarefa\s+Objetivo\s+da\s+Tarefa",
    re.I,
)
CRITERION_ROW = re.compile(r"^[0-4]=\s*")
NOTE_ROW = re.compile(r"^(?:Nota:|Apêndice)", re.I)

# PDF extract reads columns in order: Nome | Objetivo | Pergunta | Exemplo | Critérios.
OBJECTIVE_OPENER = re.compile(
    r"^(?:"
    r"Quando (?:se |um |uma |o |a |lhe |é |existem|outros|tiver|começarem|apresentam|oferece|realizar|nao |não |for |há |houver|são |necessário|precisa|dois|três|existir|na )"
    r"|O estudante "
    r"|O aluno "
    r"|Em uma "
    r"|Em um "
    r"|Se tiver "
    r"|Se lhe "
    r"|Se começarem "
    r"|Indica "
    r"|Nomear "
    r"|Fazer "
    r"|Dizer "
    r"|Cantar "
    r"|Participar"
    r"|Responderá"
    r"|O reforçador "
    r"|Completar (?:palavras|frases|a palavra|a frase|as letras|as palavras|com |uma tarefa,|uma frase)"
    r"|Manter "
    r"|Mostrar "
    r"|Aceitar "
    r"|Procurar "
    r"|Imitar "
    r"|Vocalizar "
    r"|Seguir "
    r"|Identificar "
    r"|Contar "
    r"|Ler "
    r"|Escrever "
    r"|Copiar "
    r"|Depois de "
    r"|Quando um "
    r"|Quando uma "
    r"|Compre-la "
    r"|O estudante poderá "
    r"|O aluno poderá "
    r")",
    re.I,
)

QUESTION_OPENER = re.compile(
    r"^(?:"
    r"Demonstra "
    r"|Pegará "
    r"|Nomeia "
    r"|Usa "
    r"|Pode "
    r"|Coloque "
    r"|Segue "
    r"|Responde "
    r"|Levanta "
    r"|Senta "
    r"|Veste "
    r"|Come "
    r"|Bebe "
    r"|Faz "
    r"|Canta "
    r"|Completa "
    r"|Imita "
    r"|Identifica "
    r"|Conta "
    r"|Lê "
    r"|Escreve "
    r"|Iguala "
    r"|Soletra "
    r"|Chuta "
    r"|Pega "
    r"|Quando participa"
    r"|Quando lhe "
    r"|Quando é perguntado"
    r"|Quando o estudante "
    r"|Qual "
    r"|Quantos "
    r"|Quem "
    r"|Onde "
    r"|Como "
    r"|O aluno irá"
    r"|O estudante irá"
    r"|Olhará "
    r"|Olha "
    r"|Seguirá "
    r"|Permite "
    r"|Possui "
    r"|Brinca "
    r"|Explora "
    r"|Procura "
    r"|Espera "
    r"|Aguarda "
    r"|Pede "
    r"|Solicita "
    r"|Indica "
    r"|Escolhe "
    r"|Seleciona "
    r"|Toca "
    r"|Aponta "
    r"|Trabalha "
    r"|Procura a "
    r"|Compartilha "
    r"|Oferece "
    r"|Começará "
    r"|Chama "
    r"|Entrega "
    r"|Mostra "
    r"|Subir "
    r"|Descer "
    r"|Calça "
    r"|Calçar "
    r"|Vestir "
    r"|Veste "
    r"|Come "
    r"|Bebe "
    r"|Lava "
    r"|Seca "
    r"|Penteia "
    r"|Escova "
    r"|Assoa "
    r"|Urina "
    r"|Defeca "
    r"|Utiliza "
    r"|Controla "
    r"|Caminha "
    r"|Corre "
    r"|Pula "
    r"|Arremessa "
    r"|Rola "
    r"|Equilibra "
    r"|Gira "
    r"|Balança "
    r"|Caminha "
    r"|Corre "
    r"|Ajoelha"
    r"|Agacha"
    r"|Gallopa"
    r"|Galopa"
    r"|Salta "
    r"|Pula "
    r"|Nada "
    r"|Rema "
    r"|Pedala "
    r"|Anda "
    r")",
    re.I,
)


def _join_lines(lines: list[str]) -> str:
    return re.sub(r"\s+", " ", " ".join(lines)).strip()


def _preprocess_lines(lines: list[str]) -> list[str]:
    """Split lines where question and criteria were merged (common in Y/Z)."""
    out: list[str] = []
    for line in lines:
        if re.search(r"\?\s*\d=", line):
            q_part, crit_part = re.split(r"(?<=\?)\s*(?=\d=)", line, maxsplit=1)
            out.append(q_part.strip())
            if crit_part.strip():
                out.append(crit_part.strip())
            continue
        # Example + criteria on same line without '?' (Y/Z motor items).
        if re.search(r"\s\d=\s", line) and not CRITERION_ROW.match(line):
            body_part, crit_part = re.split(r"\s(?=\d=)", line, maxsplit=1)
            if body_part.strip():
                out.append(body_part.strip())
            if crit_part.strip():
                out.append(crit_part.strip())
            continue
        out.append(line)
    return out


def _split_motor_style(body: list[str]) -> dict[str, str] | None:
    """Y/Z rows: 'Nome O estudante poderá' then 'Nome Pergunta? exemplo'."""
    if not body or len(body) > 6:
        return None
    first = body[0]
    if not re.search(r"\sO estudante poderá\s*$", first, re.I):
        return None
    task_name, _ = re.split(r"\s+O estudante poderá\s*$", first, maxsplit=1, flags=re.I)
    if len(body) >= 2 and "?" in body[1]:
        q_line = body[1]
        q_match = re.search(r"(.+?\?)", q_line)
        question = q_match.group(1).strip() if q_match else q_line.strip()
        example_tail = q_line[q_match.end() :].strip() if q_match else ""
        example_lines = ([example_tail] if example_tail else []) + body[2:]
        return {
            "task_name": task_name.strip(),
            "objective": f"O estudante poderá {task_name.strip()}",
            "question": question,
            "example": _join_lines([ln for ln in example_lines if ln and not CRITERION_ROW.match(ln)]),
            "criteria": "",
            "notes": "",
        }
    return None


def _split_compact_line(line: str) -> dict[str, str] | None:
    """Parse single-line motor tasks: 'Nome O aluno poderá Nome Pergunta? N= ...'."""
    m = re.match(
        r"^(?P<name>.+?)\s+(?P<obj>O aluno poderá\s+.+?)\s+(?P<q>.+?\?)\s*(?P<crit>\d=.+)$",
        line,
        re.I,
    )
    if not m:
        return None
    return {
        "task_name": m.group("name").strip(),
        "objective": m.group("obj").strip(),
        "question": m.group("q").strip(),
        "example": "",
        "criteria": m.group("crit").strip(),
        "notes": "",
    }


def _split_criteria(lines: list[str]) -> tuple[list[str], list[str]]:
    """Criteria column is last — split at first line matching N=."""
    first_crit = next((i for i, line in enumerate(lines) if CRITERION_ROW.match(line)), None)
    if first_crit is None:
        return lines, []

    body = lines[:first_crit]
    criteria_merged: list[str] = []
    for line in lines[first_crit:]:
        if NOTE_ROW.match(line):
            body.append(line)
            continue
        if CRITERION_ROW.match(line):
            criteria_merged.append(line)
        elif criteria_merged and not HEADER_ROW.search(line):
            criteria_merged[-1] = f"{criteria_merged[-1]} {line}"
    return body, criteria_merged


def _objective_start(body: list[str]) -> int:
    for i, line in enumerate(body):
        if OBJECTIVE_OPENER.match(line.strip()):
            return i
    # ponytail: if no opener, first line is usually task name only.
    return 1 if len(body) > 1 else 0


def _question_start(body: list[str], obj_start: int, task_name: str = "") -> int:
    task_first = task_name.split()[0].lower() if task_name else ""
    for i in range(obj_start, len(body)):
        if QUESTION_OPENER.match(body[i].strip()):
            return i
        if task_first and i > obj_start and body[i].lower().startswith(task_first):
            return i
    # Fallback: first line containing '?' after objective block.
    for i in range(obj_start, len(body)):
        if "?" in body[i]:
            return i
    return obj_start


def _question_end(body: list[str], q_start: int) -> int:
    last = q_start
    for i in range(q_start, len(body)):
        if "?" in body[i]:
            last = i
    return last


def _split_block(lines: list[str]) -> dict[str, str]:
    """Split PDF block using column order: Nome | Objetivo | Pergunta | Exemplo | Critérios."""
    if not lines:
        return {
            "task_name": "",
            "objective": "",
            "question": "",
            "example": "",
            "criteria": "",
            "notes": "",
        }

    lines = _preprocess_lines(lines)

    # Single-line compact motor/self-help rows.
    if len(lines) == 1:
        compact = _split_compact_line(lines[0])
        if compact:
            return compact

    body, criteria_raw = _split_criteria(lines)
    notes_lines = [ln for ln in body if NOTE_ROW.match(ln)]
    body = [ln for ln in body if not NOTE_ROW.match(ln) and not HEADER_ROW.search(ln)]

    motor = _split_motor_style(body)
    if motor:
        motor["criteria"] = "\n".join(criteria_raw) if criteria_raw else motor["criteria"]
        if motor["criteria"] and re.search(r"\d=.*\d=", motor["criteria"]):
            parts = re.findall(r"\d=\s*[^0-9]+?(?=\s*\d=|$)", motor["criteria"])
            if len(parts) > 1:
                motor["criteria"] = "\n".join(p.strip() for p in parts)
        return motor

    obj_start = _objective_start(body)
    task_name = _join_lines(body[:obj_start])

    q_start = _question_start(body, obj_start, task_name)
    q_end = _question_end(body, q_start)

    objective = _join_lines(body[obj_start:q_start])
    question = _join_lines(body[q_start : q_end + 1])
    example = _join_lines(body[q_end + 1 :])
    criteria = "\n".join(criteria_raw)
    # Unpack inline dual criteria (e.g. "1= Sim  0= Não").
    if criteria and re.search(r"\d=.*\d=", criteria):
        parts = re.findall(r"\d=\s*[^0-9]+?(?=\s*\d=|$)", criteria)
        if len(parts) > 1:
            criteria = "\n".join(p.strip() for p in parts)
    notes = _join_lines(notes_lines)

    return {
        "task_name": task_name,
        "objective": objective,
        "question": question,
        "example": example,
        "criteria": criteria,
        "notes": notes,
    }


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
