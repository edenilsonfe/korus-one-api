#!/usr/bin/env python3
"""Extract ADL-2 protocol Material/Procedimento from official PDF into JSON."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "app" / "data" / "adl-linguagem" / "protocol-details.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adl2_item_catalog import LE_ITEMS, LR_ITEMS, PREREQ_ITEMS  # noqa: E402

ITEM_START = re.compile(r"^m\s+(\d+)\.\s+(.+)$")


def pdf_text(pdf_path: Path) -> str:
    result = subprocess.run(
        ["pdftotext", str(pdf_path), "-"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s).strip().lower()


def title_catalog() -> dict[str, tuple[str, int]]:
    catalog: dict[str, tuple[str, int]] = {}
    for item in PREREQ_ITEMS:
        catalog[norm(item["text"])] = ("PRE", int(item["item_number"]))
    for num, (_, _, title) in LR_ITEMS.items():
        catalog[norm(title)] = ("LR", num)
    for num, (_, _, title) in LE_ITEMS.items():
        catalog[norm(title)] = ("LE", num)
    return catalog


def resolve_domain(title: str, num: int, catalog: dict[str, tuple[str, int]]) -> tuple[str, int] | None:
    key = norm(title)
    if key in catalog:
        return catalog[key]
    for cat_key, value in catalog.items():
        if key.startswith(cat_key[:40]) or cat_key.startswith(key[:40]):
            return value
    if num <= 2 and "atencao" in key:
        return ("PRE", num)
    return None


def parse_items(text: str) -> dict[str, dict[str, dict]]:
    catalog = title_catalog()
    details: dict[str, dict[str, dict]] = {"PRE": {}, "LR": {}, "LE": {}}
    current_num: int | None = None
    current_domain: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer, current_num, current_domain
        if current_num is None or current_domain is None:
            buffer = []
            return
        body = "\n".join(buffer).strip()
        material = ""
        procedure = ""
        scoring = ""
        if "Material:" in body:
            parts = body.split("Material:", 1)[1]
            if "Procedimento:" in parts:
                material, rest = parts.split("Procedimento:", 1)
                if re.search(r"1 ponto:", rest, re.I):
                    procedure, scoring = re.split(r"1 ponto:", rest, maxsplit=1, flags=re.I)
                else:
                    procedure = rest
            else:
                material = parts
        elif "Procedimento:" in body:
            rest = body.split("Procedimento:", 1)[1]
            if re.search(r"1 ponto:", rest, re.I):
                procedure, scoring = re.split(r"1 ponto:", rest, maxsplit=1, flags=re.I)
            else:
                procedure = rest

        instructions = procedure.strip()
        if scoring.strip():
            instructions = f"{instructions}\n\nCritério (1 ponto): {scoring.strip()}"

        details[current_domain][str(current_num)] = {
            "material": material.strip(),
            "examiner_instructions": instructions,
        }
        buffer = []

    pending_title: str | None = None
    pending_num: int | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("ADL 2") or line.isdigit():
            continue
        if "LINGUAGEM COMPREENSIVA" in line.upper() or "LINGUAGEM EXPRESSIVA" in line.upper():
            continue
        if re.search(r"ano.*meses.*ano", line.lower()):
            continue

        m = ITEM_START.match(line)
        if m:
            flush()
            pending_num = int(m.group(1))
            pending_title = m.group(2).strip()
            resolved = resolve_domain(pending_title, pending_num, catalog)
            if resolved:
                current_domain, current_num = resolved
            else:
                current_domain = None
                current_num = None
            buffer = []
            continue

        if current_num is not None and line and not line.startswith("__"):
            buffer.append(line)

    flush()
    return details


def main() -> None:
    pdf = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.home() / "Downloads" / "Protocolo ADL2_28x21_ALT4.pdf"
    if not pdf.exists():
        raise SystemExit(f"PDF not found: {pdf}")
    details = parse_items(pdf_text(pdf))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(details, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} — { {k: len(v) for k, v in details.items()} }")


if __name__ == "__main__":
    main()
