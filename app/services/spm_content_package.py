import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_PACKAGE_PATH = Path(__file__).resolve().parent.parent / "data" / "spm_sample_package.json"


class SpmContentPackage:
    def __init__(self, data: dict[str, Any]):
        self.data = data

    @property
    def version(self) -> int:
        return int(self.data.get("version", 1))

    @property
    def scale(self) -> list[dict[str, Any]]:
        return self.data.get("scale", [])

    @property
    def domains(self) -> list[dict[str, str]]:
        return self.data.get("domains", [])

    def list_subforms(self) -> list[dict[str, Any]]:
        subforms = self.data.get("subforms", {})
        result = []
        for slug, config in subforms.items():
            item_count = int(config.get("item_count") or len(config.get("items", [])))
            if config.get("import_pending"):
                item_count = 0
            result.append(
                {
                    "slug": slug,
                    "title": config["title"],
                    "filler": config["filler"],
                    "min_age_months": config["min_age_months"],
                    "max_age_months": config["max_age_months"],
                    "item_count": item_count,
                    "import_pending": bool(config.get("import_pending")),
                }
            )
        return sorted(result, key=lambda item: item["min_age_months"])

    def get_subform(self, slug: str) -> dict[str, Any]:
        subforms = self.data.get("subforms", {})
        if slug not in subforms:
            raise KeyError(f"Sub-form '{slug}' not found in SPM package")
        return subforms[slug]

    def get_items(self, slug: str) -> list[dict[str, Any]]:
        return self.get_subform(slug).get("items", [])

    def get_norms(self, slug: str) -> dict[str, Any]:
        return self.get_subform(slug).get("norms", {})

    def get_scale_bounds(self) -> tuple[int, int]:
        scale = self.scale
        if not scale:
            return 1, 4
        values = [int(entry["value"]) for entry in scale]
        return min(values), max(values)

    def suggest_scope_for_age(self, age_months: int | None) -> dict[str, dict[str, bool]]:
        if age_months is None:
            subforms = self.list_subforms()
            return {entry["slug"]: {"required": True} for entry in subforms[:2]}

        suggested: dict[str, dict[str, bool]] = {}
        for entry in self.list_subforms():
            if entry["import_pending"] or entry["item_count"] <= 0:
                continue
            if entry["min_age_months"] <= age_months <= entry["max_age_months"]:
                suggested[entry["slug"]] = {"required": entry["filler"] == "external"}

        if not suggested:
            candidates = [e for e in self.list_subforms() if e["item_count"] > 0]
            if not candidates:
                return {}
            closest = min(
                candidates,
                key=lambda item: min(
                    abs(age_months - item["min_age_months"]),
                    abs(age_months - item["max_age_months"]),
                ),
            )
            suggested[closest["slug"]] = {"required": True}

        return suggested

    def public_items_payload(self, slug: str) -> list[dict[str, Any]]:
        return [
            {"id": item["id"], "domain": item["domain"], "text": item["text"]}
            for item in self.get_items(slug)
        ]


def _load_package_from_path(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)

    data_dir = path.parent
    subforms = data.get("subforms", {})
    for config in subforms.values():
        items_file = config.get("items_file")
        if not items_file:
            continue
        items_path = data_dir / items_file
        if not items_path.is_file():
            logger.warning("SPM items_file %s not found for subform", items_file)
            continue
        with items_path.open(encoding="utf-8") as handle:
            config["items"] = json.load(handle)

    return data


@lru_cache(maxsize=1)
def get_spm_content_package() -> SpmContentPackage:
    settings = get_settings()
    configured = settings.spm_content_package_path
    if configured:
        path = Path(configured)
        if not path.is_file():
            path = DEFAULT_PACKAGE_PATH
    else:
        path = DEFAULT_PACKAGE_PATH
    return SpmContentPackage(_load_package_from_path(path))
