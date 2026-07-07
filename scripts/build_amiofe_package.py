#!/usr/bin/env python3
"""Generate AMIOFE-E package items and manifest from official protocol catalog."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "app" / "data" / "amiofe"
ITEMS_DIR = DATA / "items"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from amiofe_e_item_catalog import (  # noqa: E402
    ANALISE_OCLUSAL_ITEMS,
    BOCHECHAS_ITEMS,
    DEGLUTICAO_EFICIENCIA_ITEMS,
    DEGLUTICAO_LABIOS_ITEMS,
    DEGLUTICAO_LINGUA_ITEMS,
    DEGLUTICAO_SINAIS_ITEMS,
    FACE_ITEMS,
    IDENTIFICACAO_ITEMS,
    LABIOS_ITEMS,
    LINGUA_ITEMS,
    MASTIGACAO_MORDIDA_ITEMS,
    MASTIGACAO_PADRAO_ITEMS,
    MASTIGACAO_SINAIS_ITEMS,
    MENTUAL_ITEMS,
    MOB_BOCHECHAS_ITEMS,
    MOB_LABIAL_ITEMS,
    MOB_LINGUA_ITEMS,
    MOB_MANDIBULA_ITEMS,
    PALATO_ITEMS,
    RELACAO_MANDIBULAR_ITEMS,
    RESPIRACAO_ITEMS,
)

SCALE_4 = [
    {"value": 4, "label": "Normal (4)"},
    {"value": 3, "label": "Leve (3)"},
    {"value": 2, "label": "Moderado (2)"},
    {"value": 1, "label": "Severo (1)"},
]

SCALE_6 = [
    {"value": 6, "label": "Normal (6)"},
    {"value": 5, "label": "Habilidade insuficiente (5)"},
    {"value": 4, "label": "Insuficiente com movimentos associados (4)"},
    {"value": 3, "label": "Insuficiente com tremor (3)"},
    {"value": 2, "label": "Insuficiente com associados e tremor (2)"},
    {"value": 1, "label": "Ausência de habilidade (1)"},
]

SCALE_6_DEG_LABIOS = [
    {"value": 6, "label": "Vedam sem esforço aparente (6)"},
    {"value": 4, "label": "Vedam com contração/interposição leve (4)"},
    {"value": 3, "label": "Moderada (3)"},
    {"value": 2, "label": "Severa (2)"},
    {"value": 1, "label": "Não vedam a cavidade oral (1)"},
]

SCALE_10_MAST = [
    {"value": 10, "label": "Bilateral alternada 50/50–40/60 (10)"},
    {"value": 8, "label": "Simultânea vertical (8)"},
    {"value": 6, "label": "Unilateral preferencial grau 1 (6)"},
    {"value": 4, "label": "Unilateral preferencial grau 2 (4)"},
    {"value": 2, "label": "Unilateral crônica (2)"},
    {"value": 1, "label": "Não tritura / anterior (1–2)"},
]

SCALE_3 = [
    {"value": 3, "label": "Não repete deglutição (3)"},
    {"value": 2, "label": "Uma repetição (2)"},
    {"value": 1, "label": "Deglutições múltiplas (1)"},
]

SCALE_2_ABSENT_BETTER = [
    {"value": 2, "label": "Ausente (2)"},
    {"value": 1, "label": "Presente (1)"},
]

SCALE_LEGACY_0_3 = [
    {"value": 3, "label": "Plenamente adequado (3)"},
    {"value": 2, "label": "Adequado (2)"},
    {"value": 1, "label": "Parcialmente adequado (1)"},
    {"value": 0, "label": "Inadequado / ausente (0)"},
]


def _scale_items(prefix: str, domain: str, rows: list[tuple[str, str, int]]) -> list[dict]:
    return [
        {
            "id": f"{prefix}_{suffix}",
            "domain": domain,
            "text": text,
            "max_points": max_pts,
            "input_type": "scale",
        }
        for suffix, text, max_pts in rows
    ]


def _text_items(prefix: str, domain: str, rows: list[tuple[str, str]]) -> list[dict]:
    return [
        {"id": f"{prefix}_{suffix}", "domain": domain, "text": text, "input_type": "text"}
        for suffix, text in rows
    ]


# v1 slugs — baterias criadas antes da migração AMIOFE-E
LEGACY_MODULES: list[dict] = [
    {
        "slug": "historia",
        "title": "História clínica (legado)",
        "domain": "historia",
        "kind": "qualitative",
        "file": "legacy/historia.json",
        "items": _text_items("hist", "historia", [
            ("anamnese", "Anamnese"),
            ("antecedentes", "Antecedentes"),
            ("medicamentos", "Medicamentos"),
        ]),
    },
    {
        "slug": "mobilidade",
        "title": "Mobilidade orofacial (legado)",
        "domain": "mobilidade",
        "kind": "observational",
        "scale": SCALE_LEGACY_0_3,
        "max_sum": 12,
        "file": "legacy/mobilidade.json",
        "items": _scale_items("mob", "mobilidade", [
            ("abertura", "Abertura mandibular", 3),
            ("fechamento", "Fechamento mandibular", 3),
            ("rapidos", "Movimentos rápidos", 3),
            ("resistencia", "Resistência à movimentação", 3),
        ]),
    },
    {
        "slug": "mastigacao",
        "title": "Mastigação (legado)",
        "domain": "mastigacao",
        "kind": "observational",
        "scale": SCALE_LEGACY_0_3,
        "max_sum": 12,
        "file": "legacy/mastigacao.json",
        "items": _scale_items("mast", "mastigacao", [
            ("padrao", "Padrão de mastigação", 3),
            ("residuo", "Resíduo oral", 3),
            ("tempo", "Tempo de mastigação", 3),
            ("forca", "Força mastigatória", 3),
        ]),
    },
    {
        "slug": "degluticao",
        "title": "Deglutição (legado)",
        "domain": "degluticao",
        "kind": "observational",
        "scale": SCALE_LEGACY_0_3,
        "max_sum": 12,
        "file": "legacy/degluticao.json",
        "items": _scale_items("deg", "degluticao", [
            ("reflexo", "Reflexo de deglutição", 3),
            ("fases", "Fases da deglutição", 3),
            ("escape", "Escape oral/nasal", 3),
            ("tosse", "Tosse pós-deglutição", 3),
        ]),
    },
    {
        "slug": "fala",
        "title": "Fala (legado)",
        "domain": "fala",
        "kind": "observational",
        "scale": SCALE_LEGACY_0_3,
        "max_sum": 12,
        "file": "legacy/fala.json",
        "items": _scale_items("fala", "fala", [
            ("articulacao", "Articulação", 3),
            ("diccao", "Díção e inteligibilidade", 3),
            ("ritmo", "Ritmo e fluência", 3),
            ("resistencia", "Resistência em exercícios", 3),
        ]),
    },
]


MODULES: list[dict] = [
    {
        "slug": "identificacao",
        "title": "Identificação e queixa",
        "domain": "identificacao",
        "kind": "qualitative",
        "file": "identificacao.json",
        "items": _text_items("id", "identificacao", IDENTIFICACAO_ITEMS),
    },
    {
        "slug": "face",
        "title": "Face",
        "domain": "face",
        "kind": "observational",
        "scale": SCALE_4,
        "max_sum": 12,
        "file": "face.json",
        "items": _scale_items("face", "face", FACE_ITEMS),
    },
    {
        "slug": "bochechas",
        "title": "Bochechas",
        "domain": "bochechas",
        "kind": "observational",
        "scale": SCALE_4,
        "max_sum": 8,
        "file": "bochechas.json",
        "items": _scale_items("bochechas", "bochechas", BOCHECHAS_ITEMS),
    },
    {
        "slug": "relacao-mandibular",
        "title": "Relação mandíbula/maxila",
        "domain": "relacao_mandibular",
        "kind": "observational",
        "scale": SCALE_4,
        "max_sum": 12,
        "file": "relacao-mandibular.json",
        "items": _scale_items("rm", "relacao_mandibular", RELACAO_MANDIBULAR_ITEMS),
    },
    {
        "slug": "labios",
        "title": "Lábios",
        "domain": "labios",
        "kind": "observational",
        "scale": SCALE_4,
        "max_sum": 12,
        "file": "labios.json",
        "items": _scale_items("lab", "labios", LABIOS_ITEMS),
    },
    {
        "slug": "musculo-mentual",
        "title": "Músculo mentual",
        "domain": "mentual",
        "kind": "observational",
        "scale": SCALE_4,
        "max_sum": 4,
        "file": "musculo-mentual.json",
        "items": _scale_items("ment", "mentual", MENTUAL_ITEMS),
    },
    {
        "slug": "lingua",
        "title": "Língua",
        "domain": "lingua",
        "kind": "observational",
        "scale": SCALE_4,
        "max_sum": 8,
        "file": "lingua.json",
        "items": _scale_items("ling", "lingua", LINGUA_ITEMS),
    },
    {
        "slug": "palato",
        "title": "Palato duro",
        "domain": "palato",
        "kind": "observational",
        "scale": SCALE_4,
        "max_sum": 8,
        "file": "palato.json",
        "items": _scale_items("pal", "palato", PALATO_ITEMS),
    },
    {
        "slug": "mobilidade-lingua",
        "title": "Mobilidade — língua",
        "domain": "mobilidade",
        "kind": "observational",
        "scale": SCALE_6,
        "max_sum": 36,
        "file": "mobilidade-lingua.json",
        "items": _scale_items("ml", "mobilidade", MOB_LINGUA_ITEMS),
    },
    {
        "slug": "mobilidade-labial",
        "title": "Mobilidade — lábios",
        "domain": "mobilidade",
        "kind": "observational",
        "scale": SCALE_6,
        "max_sum": 24,
        "file": "mobilidade-labial.json",
        "items": _scale_items("mlb", "mobilidade", MOB_LABIAL_ITEMS),
    },
    {
        "slug": "mobilidade-mandibula",
        "title": "Mobilidade — mandíbula",
        "domain": "mobilidade",
        "kind": "observational",
        "scale": SCALE_6,
        "max_sum": 30,
        "file": "mobilidade-mandibula.json",
        "items": _scale_items("mm", "mobilidade", MOB_MANDIBULA_ITEMS),
    },
    {
        "slug": "mobilidade-bochechas",
        "title": "Mobilidade — bochechas",
        "domain": "mobilidade",
        "kind": "observational",
        "scale": SCALE_6,
        "max_sum": 24,
        "file": "mobilidade-bochechas.json",
        "items": _scale_items("mb", "mobilidade", MOB_BOCHECHAS_ITEMS),
    },
    {
        "slug": "respiracao",
        "title": "Respiração",
        "domain": "respiracao",
        "kind": "observational",
        "scale": SCALE_4,
        "max_sum": 4,
        "file": "respiracao.json",
        "items": _scale_items("resp", "respiracao", RESPIRACAO_ITEMS),
    },
    {
        "slug": "degluticao-labios",
        "title": "Deglutição — lábios",
        "domain": "degluticao",
        "kind": "observational",
        "scale": SCALE_6_DEG_LABIOS,
        "max_sum": 6,
        "file": "degluticao-labios.json",
        "items": _scale_items("deg_lab", "degluticao", DEGLUTICAO_LABIOS_ITEMS),
    },
    {
        "slug": "degluticao-lingua",
        "title": "Deglutição — língua",
        "domain": "degluticao",
        "kind": "observational",
        "scale": SCALE_4,
        "max_sum": 4,
        "file": "degluticao-lingua.json",
        "items": _scale_items("deg_ling", "degluticao", DEGLUTICAO_LINGUA_ITEMS),
    },
    {
        "slug": "degluticao-sinais",
        "title": "Deglutição — sinais associados",
        "domain": "degluticao",
        "kind": "observational",
        "scale": SCALE_2_ABSENT_BETTER,
        "max_sum": 12,
        "file": "degluticao-sinais.json",
        "items": _scale_items("deg_sin", "degluticao", DEGLUTICAO_SINAIS_ITEMS),
    },
    {
        "slug": "degluticao-eficiencia",
        "title": "Deglutição — eficiência",
        "domain": "degluticao",
        "kind": "observational",
        "scale": SCALE_3,
        "max_sum": 6,
        "file": "degluticao-eficiencia.json",
        "items": _scale_items("deg_eff", "degluticao", DEGLUTICAO_EFICIENCIA_ITEMS),
    },
    {
        "slug": "mastigacao-padrao",
        "title": "Mastigação — padrão",
        "domain": "mastigacao",
        "kind": "observational",
        "scale": SCALE_10_MAST,
        "max_sum": 10,
        "file": "mastigacao-padrao.json",
        "items": _scale_items("mast_pad", "mastigacao", MASTIGACAO_PADRAO_ITEMS),
    },
    {
        "slug": "mastigacao-sinais",
        "title": "Mastigação — sinais associados",
        "domain": "mastigacao",
        "kind": "observational",
        "scale": SCALE_2_ABSENT_BETTER,
        "max_sum": 6,
        "file": "mastigacao-sinais.json",
        "items": _scale_items("mast_sin", "mastigacao", MASTIGACAO_SINAIS_ITEMS),
    },
    {
        "slug": "mastigacao-mordida",
        "title": "Mastigação — mordida",
        "domain": "mastigacao",
        "kind": "observational",
        "scale": SCALE_4,
        "max_sum": 4,
        "file": "mastigacao-mordida.json",
        "items": _scale_items("mast_mord", "mastigacao", MASTIGACAO_MORDIDA_ITEMS),
    },
    {
        "slug": "analise-oclusal",
        "title": "Análise da oclusão",
        "domain": "oclusao",
        "kind": "qualitative",
        "required": False,
        "file": "analise-oclusal.json",
        "items": _text_items("ocl", "oclusao", ANALISE_OCLUSAL_ITEMS),
    },
]


def build_manifest() -> dict:
    modules: dict[str, dict] = {}
    subtests: list[dict] = []

    for mod in MODULES:
        slug = mod["slug"]
        entry: dict = {
            "id": slug,
            "title": mod["title"],
            "domain": mod["domain"],
            "module_kind": mod["kind"],
            "items_file": f"items/{mod['file']}",
            "item_count": len(mod["items"]),
            "filler": "clinician",
        }
        if mod.get("scale"):
            entry["scale"] = mod["scale"]
        if mod.get("max_sum"):
            entry["max_sum"] = mod["max_sum"]
        if mod.get("required") is False:
            entry["required"] = False
        modules[slug] = entry
        subtests.append(
            {
                "id": slug,
                "title": mod["title"],
                "item_count": len(mod["items"]),
                **({"required": False} if mod.get("required") is False else {}),
            }
        )

    domain_titles = {
        "identificacao": "Identificação",
        "face": "Face",
        "bochechas": "Bochechas",
        "relacao_mandibular": "Relação mandibular",
        "labios": "Lábios",
        "mentual": "Músculo mentual",
        "lingua": "Língua",
        "palato": "Palato",
        "mobilidade": "Mobilidade",
        "respiracao": "Respiração",
        "degluticao": "Deglutição",
        "mastigacao": "Mastigação",
        "oclusao": "Oclusão",
        "historia": "História clínica",
        "fala": "Fala",
    }

    legacy_modules: dict[str, dict] = {}
    for mod in LEGACY_MODULES:
        slug = mod["slug"]
        entry: dict = {
            "id": slug,
            "title": mod["title"],
            "domain": mod["domain"],
            "module_kind": mod["kind"],
            "items_file": f"items/{mod['file']}",
            "item_count": len(mod["items"]),
            "filler": "clinician",
            "required": False,
            "deprecated": True,
        }
        if mod.get("scale"):
            entry["scale"] = mod["scale"]
        if mod.get("max_sum"):
            entry["max_sum"] = mod["max_sum"]
        legacy_modules[slug] = entry

    return {
        "version": 3,
        "package_id": "amiofe-e-br-v1",
        "instrument_slug": "amiofe",
        "instrument_title": "AMIOFE-E — Avaliação Miofuncional Orofacial com Escores Expandido",
        "license_ref": "Felicio2010-REPRODUCTION-CITED",
        "content_status": "official-structure",
        "norms_region": "BR",
        "norms_file": "norms-br.json",
        "archetype": "observational",
        "supports_multi_session": True,
        "scale": SCALE_4,
        "domains": [{"id": k, "title": v} for k, v in domain_titles.items()],
        "modules": modules,
        "legacy_modules": legacy_modules,
        "subtests": subtests,
        "scoring": {
            "engine": "observational_domains",
            "scale_direction": "higher_is_better",
            "interpretations": [
                {"min": 0, "max": 59, "level": "altered", "label": "Função orofacial inadequada"},
                {"min": 60, "max": 79, "level": "attention", "label": "Função parcialmente adequada"},
                {"min": 80, "max": 100, "level": "expected", "label": "Função orofacial adequada"},
            ],
            "total_score": {
                "reference_max": 103,
                "normalize": True,
                "dmo_cutoff": 89,
                "dmo_cutoff_child": 89,
                "child_age_months_max": 144,
                "reference_mean_adult": 95.0,
                "reference_sd_adult": 4.0,
                "reference_mean_child": 92.0,
                "reference_sd_child": 3.0,
                "categories": [
                    {
                        "id": "aparencia",
                        "title": "Aparência e postura",
                        "modules": [
                            "face",
                            "bochechas",
                            "relacao-mandibular",
                            "labios",
                            "musculo-mentual",
                            "lingua",
                            "palato",
                        ],
                        "max_sum": 64,
                    },
                    {
                        "id": "mobilidade",
                        "title": "Mobilidade",
                        "modules": [
                            "mobilidade-lingua",
                            "mobilidade-labial",
                            "mobilidade-mandibula",
                            "mobilidade-bochechas",
                        ],
                        "max_sum": 114,
                    },
                    {
                        "id": "funcoes",
                        "title": "Funções",
                        "modules": [
                            "respiracao",
                            "degluticao-labios",
                            "degluticao-lingua",
                            "degluticao-sinais",
                            "degluticao-eficiencia",
                            "mastigacao-padrao",
                            "mastigacao-sinais",
                            "mastigacao-mordida",
                        ],
                        "max_sum": 52,
                    },
                ],
                "classification_adult": [
                    {"min": 91, "max": 103, "level": "expected", "label": "Normal — sem DMO"},
                    {"min": 87, "max": 90, "level": "attention", "label": "DMO muito leve"},
                    {"min": 83, "max": 86, "level": "mild", "label": "DMO leve"},
                    {"min": 79, "max": 82, "level": "moderate", "label": "DMO moderado"},
                    {"min": 0, "max": 78, "level": "altered", "label": "DMO severo"},
                ],
                "classification_child": [
                    {"min": 89, "max": 103, "level": "expected", "label": "Normal — sem DMO"},
                    {"min": 86, "max": 88, "level": "attention", "label": "DMO muito leve"},
                    {"min": 83, "max": 85, "level": "mild", "label": "DMO leve"},
                    {"min": 80, "max": 82, "level": "moderate", "label": "DMO moderado"},
                    {"min": 0, "max": 79, "level": "altered", "label": "DMO severo"},
                ],
            },
        },
        "report": {
            "template_id": "amiofe-e-br-v1",
            "sections": ["identificacao", "resultados", "interpretacao", "recomendacoes"],
        },
        "informant_forms": [],
    }


def main() -> None:
    ITEMS_DIR.mkdir(parents=True, exist_ok=True)
    legacy_dir = ITEMS_DIR / "legacy"
    legacy_dir.mkdir(parents=True, exist_ok=True)
    for mod in MODULES:
        path = ITEMS_DIR / mod["file"]
        path.write_text(json.dumps(mod["items"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote {path.name}: {len(mod['items'])} items")

    for mod in LEGACY_MODULES:
        path = legacy_dir / Path(mod["file"]).name
        path.write_text(json.dumps(mod["items"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote legacy/{path.name}: {len(mod['items'])} items")

    manifest = build_manifest()
    manifest_path = DATA / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote manifest.json: {len(manifest['modules'])} modules")


if __name__ == "__main__":
    main()
