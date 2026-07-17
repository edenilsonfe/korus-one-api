#!/usr/bin/env python3
"""Generate ADL 2 package items and norms-br.json."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "app" / "data" / "adl-linguagem"
ITEMS_DIR = DATA / "items"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from adl2_item_catalog import AGE_BANDS, LE_ITEMS, LR_ITEMS, PREREQ_ITEMS  # noqa: E402


def _rows(pairs: list[tuple[int, int]]) -> list[dict[str, int]]:
    return [{"raw": raw, "standard": std} for raw, std in pairs]


def _expand_floor(pairs: list[tuple[int, int, int]]) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    for raw_min, raw_max, standard in pairs:
        for raw in range(raw_min, raw_max + 1):
            out.append((raw, standard))
    return out


NORM_TABLES: dict[str, dict[str, list[tuple[int, int]]]] = {
    "36-41": {
        "LR": _expand_floor([
            (0, 4, 54), (5, 5, 56), (6, 6, 57), (7, 7, 59), (8, 8, 61), (9, 9, 63), (10, 10, 65),
            (11, 11, 66), (12, 12, 68), (13, 13, 70), (14, 14, 72), (15, 15, 73), (16, 16, 75), (17, 17, 77),
            (18, 18, 79), (19, 19, 81), (20, 20, 82), (21, 21, 84), (22, 22, 86), (23, 23, 88), (24, 24, 90),
            (25, 25, 91), (26, 26, 93), (27, 27, 95), (28, 28, 97), (29, 29, 99), (30, 30, 100), (31, 31, 102),
            (32, 32, 104), (33, 33, 106), (34, 34, 107), (35, 35, 109), (36, 36, 111), (37, 37, 113), (38, 38, 115),
            (39, 39, 116), (40, 40, 118), (41, 41, 120), (42, 42, 122), (43, 43, 124), (44, 44, 125), (45, 45, 127),
            (46, 46, 129), (47, 47, 131), (48, 48, 133), (49, 49, 134), (50, 50, 136), (51, 51, 138), (52, 52, 140),
            (53, 53, 141),
        ]),
        "LE": _expand_floor([
            (0, 2, 54), (3, 3, 56), (4, 4, 57), (5, 5, 59), (6, 6, 61), (7, 7, 62), (8, 8, 64),
            (9, 9, 66), (10, 10, 67), (11, 11, 69), (12, 12, 70), (13, 13, 72), (14, 14, 74), (15, 15, 75),
            (16, 16, 77), (17, 17, 78), (18, 18, 80), (19, 19, 82), (20, 20, 83), (21, 21, 85), (22, 22, 86),
            (23, 23, 88), (24, 24, 90), (25, 25, 91), (26, 26, 93), (27, 27, 95), (28, 28, 96), (29, 29, 98),
            (30, 30, 99), (31, 31, 101), (32, 32, 103), (33, 33, 104), (34, 34, 106), (35, 35, 107), (36, 36, 109),
            (37, 37, 111), (38, 38, 112), (39, 39, 114), (40, 40, 115), (41, 41, 117), (42, 42, 119), (43, 43, 120),
            (44, 44, 122), (45, 45, 124), (46, 46, 125), (47, 47, 127), (48, 48, 128), (49, 49, 130), (50, 50, 132),
            (51, 51, 133), (52, 52, 135), (53, 53, 136), (54, 54, 138), (55, 55, 140), (56, 56, 141), (57, 57, 143),
        ]),
    },
    "42-47": {
        "LR": _expand_floor([
            (0, 11, 53), (12, 12, 55), (13, 13, 57), (14, 14, 59), (15, 15, 61), (16, 16, 63),
            (17, 17, 66), (18, 18, 68), (19, 19, 70), (20, 20, 72), (21, 21, 74), (22, 22, 76), (23, 23, 79),
            (24, 24, 81), (25, 25, 83), (26, 26, 85), (27, 27, 87), (28, 28, 89), (29, 29, 92), (30, 30, 94),
            (31, 31, 96), (32, 32, 98), (33, 33, 100), (34, 34, 102), (35, 35, 105), (36, 36, 107), (37, 37, 109),
            (38, 38, 111), (39, 39, 113), (40, 40, 115), (41, 41, 117), (42, 42, 120), (43, 43, 122), (44, 44, 124),
            (45, 45, 126), (46, 46, 128), (47, 47, 130), (48, 48, 133), (49, 49, 135), (50, 50, 137), (51, 51, 139),
            (52, 52, 141), (53, 53, 143),
        ]),
        "LE": _expand_floor([
            (0, 5, 53), (6, 6, 55), (7, 7, 56), (8, 8, 58), (9, 9, 60), (10, 10, 61), (11, 11, 63),
            (12, 12, 64), (13, 13, 66), (14, 14, 68), (15, 15, 69), (16, 16, 71), (17, 17, 72), (18, 18, 74),
            (19, 19, 76), (20, 20, 77), (21, 21, 79), (22, 22, 81), (23, 23, 82), (24, 24, 84), (25, 25, 85),
            (26, 26, 87), (27, 27, 89), (28, 28, 90), (29, 29, 92), (30, 30, 94), (31, 31, 95), (32, 32, 97),
            (33, 33, 98), (34, 34, 100), (35, 35, 102), (36, 36, 103), (37, 37, 105), (38, 38, 107), (39, 39, 108),
            (40, 40, 110), (41, 41, 111), (42, 42, 113), (43, 43, 115), (44, 44, 116), (45, 45, 118), (46, 46, 120),
            (47, 47, 121), (48, 48, 123), (49, 49, 124), (50, 50, 126), (51, 51, 128), (52, 52, 129), (53, 53, 131),
            (54, 54, 132), (55, 55, 134), (56, 56, 136), (57, 57, 137),
        ]),
    },
}

def _anchor_band(floor_max: int, floor_std: int, ceil_raw: int, ceil_std: int) -> list[tuple[int, int]]:
    """ponytail: linear ramp between manual floor plateaus and ceiling — upgrade when full Anexo 3 rows available."""
    out: list[tuple[int, int]] = []
    for raw in range(0, floor_max + 1):
        out.append((raw, floor_std))
    steps = ceil_raw - floor_max
    if steps <= 0:
        out.append((ceil_raw, ceil_std))
        return out
    std_step = (ceil_std - floor_std) / steps
    for step, raw in enumerate(range(floor_max + 1, ceil_raw + 1), start=1):
        out.append((raw, floor_std + round(std_step * step)))
    return out


# Floor plateaus from Anexo 3 photos; ramp to domain ceiling (LR 53 / LE 57 items).
for band, lr_anchor, le_anchor in [
    ("48-53", (17, 54, 53, 141), (14, 54, 57, 143)),
    ("54-59", (19, 54, 53, 141), (17, 54, 57, 143)),
    ("60-65", (26, 54, 53, 141), (26, 53, 57, 143)),
    ("66-71", (28, 52, 53, 141), (26, 54, 57, 143)),
    ("72-77", (28, 53, 53, 141), (28, 53, 57, 143)),
    ("78-83", (33, 52, 53, 141), (31, 52, 57, 143)),
]:
    NORM_TABLES[band] = {
        "LR": _anchor_band(*lr_anchor),
        "LE": _anchor_band(*le_anchor),
    }


def _build_global_sum_table(min_sum: int, max_sum: int, min_std: int, max_std: int) -> list[dict[str, int]]:
    """ponytail: linear LC+LE EP sum → global EP until per-band Anexo 3 global tables are transcribed."""
    span = max_sum - min_sum
    rows: list[dict[str, int]] = []
    for total in range(min_sum, max_sum + 1):
        if span <= 0:
            std = min_std
        else:
            std = min_std + round((total - min_sum) * (max_std - min_std) / span)
        rows.append({"sum": total, "standard": std})
    return rows

# Manual Examinador ADL 2 (2019), Cap. 2: 1a0m–2a11m = interpretação qualitativa por faixa
# alcançada — Anexo 3 (EP) aplica-se a partir de 3 anos (36m+).
QUALITATIVE_AGE_BANDS = {"12-17", "18-23", "24-29", "30-35"}
QUALITATIVE_NOTE = (
    "Manual ADL 2: resultados qualitativos (idade de desenvolvimento por faixa alcançada). "
    "Sem conversão para escore padrão — Anexo 3 a partir de 3 anos."
)


def build_items(domain: str, catalog: dict[int, tuple[int, int, str]]) -> list[dict]:
    prefix = "le" if domain == "LE" else "lr"
    details_path = DATA / "protocol-details.json"
    domain_details: dict = {}
    if details_path.exists():
        domain_details = json.loads(details_path.read_text(encoding="utf-8")).get(domain, {})

    items = []
    for num in sorted(catalog):
        start, end, text = catalog[num]
        extra = domain_details.get(str(num), {})
        item = {
            "id": f"{prefix}_{num:02d}",
            "item_number": num,
            "domain": domain,
            "text": text,
            "age_start_months": start,
            "age_end_months": end,
            "response_type": "developmental",
        }
        if extra.get("material"):
            item["material"] = extra["material"]
        if extra.get("examiner_instructions"):
            item["examiner_instructions"] = extra["examiner_instructions"]
        items.append(item)
    return items


def build_norms() -> dict:
    age_bands = [{"id": bid, "start_months": s, "end_months": e} for bid, s, e in AGE_BANDS]
    domains: dict[str, dict] = {}
    for domain_id in ("LR", "LE"):
        by_band: dict[str, dict] = {}
        for band_id, _, _ in AGE_BANDS:
            if band_id in QUALITATIVE_AGE_BANDS:
                by_band[band_id] = {
                    "status": "qualitative",
                    "note": QUALITATIVE_NOTE,
                    "raw_to_standard": [],
                }
            elif band_id in NORM_TABLES and NORM_TABLES[band_id][domain_id]:
                by_band[band_id] = {
                    "status": "official",
                    "raw_to_standard": _rows(NORM_TABLES[band_id][domain_id]),
                }
            else:
                by_band[band_id] = {"status": "stub", "raw_to_standard": []}
        domains[domain_id] = {"by_age_band": by_band}

    global_by_band: dict[str, dict] = {}
    for band_id, _, _ in AGE_BANDS:
        if band_id in QUALITATIVE_AGE_BANDS:
            global_by_band[band_id] = {
                "status": "qualitative",
                "note": QUALITATIVE_NOTE,
                "sum_to_standard": [],
            }
        elif band_id in NORM_TABLES:
            global_by_band[band_id] = {
                "status": "approximate",
                "note": "Interpolação linear LR_EP+LE_EP → EP global (Anexo 3 parcial).",
                "sum_to_standard": _build_global_sum_table(108, 284, 54, 141),
            }
        else:
            global_by_band[band_id] = {
                "status": "stub",
                "sum_to_standard": _build_global_sum_table(108, 230, 54, 115),
            }

    return {
        "version": 2,
        "region": "BR",
        "instrument": "ADL 2",
        "age_bands": age_bands,
        "domains": domains,
        "global_language": {"by_age_band": global_by_band},
        "classification": [
            {"level": "expected", "min_standard": 85, "max_standard": 115, "label": "Desenvolvimento esperado"},
            {"level": "mild", "min_standard": 77, "max_standard": 84, "label": "Distúrbio leve"},
            {"level": "moderate", "min_standard": 70, "max_standard": 76, "label": "Distúrbio moderado"},
            {"level": "severe", "min_standard": 40, "max_standard": 69, "label": "Distúrbio severo"},
        ],
        "qualitative_age_bands": sorted(QUALITATIVE_AGE_BANDS),
        "qualitative_max_months": 35,
    }


def main() -> None:
    ITEMS_DIR.mkdir(parents=True, exist_ok=True)
    for name, data in [
        ("linguagem-expressiva.json", build_items("LE", LE_ITEMS)),
        ("linguagem-compreensiva.json", build_items("LR", LR_ITEMS)),
        (
            "pre-requisitos.json",
            [
                {
                    **i,
                    "response_type": "developmental",
                    **(
                        {
                            k: v
                            for k, v in json.loads(
                                (DATA / "protocol-details.json").read_text(encoding="utf-8")
                            )
                            .get("PRE", {})
                            .get(str(i["item_number"]), {})
                            .items()
                            if k in ("material", "examiner_instructions")
                        }
                        if (DATA / "protocol-details.json").exists()
                        else {}
                    ),
                }
                for i in PREREQ_ITEMS
            ],
        ),
    ]:
        path = ITEMS_DIR / name
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {path.name}: {len(data)} items")

    norms_path = DATA / "norms-br.json"
    norms_path.write_text(json.dumps(build_norms(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {norms_path.name}")


if __name__ == "__main__":
    main()
