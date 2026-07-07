import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_SAMPLES_ROOT = Path(__file__).resolve().parent.parent / "data" / "instrument_samples"
DATA_PACKAGES_ROOT = Path(__file__).resolve().parent.parent / "data"


class InstrumentContentPackage:
    def __init__(self, slug: str, data: dict[str, Any]):
        self.slug = slug
        self.data = data

    @property
    def version(self) -> int:
        return int(self.data.get("version", 1))

    @property
    def package_id(self) -> str:
        return str(self.data.get("package_id", self.slug))

    @property
    def instrument_title(self) -> str:
        return str(self.data.get("instrument_title", self.slug))

    @property
    def archetype(self) -> str:
        return str(self.data.get("archetype", "scaled"))

    @property
    def scale(self) -> list[dict[str, Any]]:
        return self.data.get("scale", [])

    @property
    def domains(self) -> list[dict[str, str]]:
        return self.data.get("domains", [])

    @property
    def scoring(self) -> dict[str, Any]:
        return self.data.get("scoring", {})

    @property
    def report(self) -> dict[str, Any]:
        return self.data.get("report", {})

    @property
    def modules(self) -> dict[str, Any]:
        return self.data.get("modules", {})

    @property
    def subtests(self) -> list[dict[str, Any]]:
        return self.data.get("subtests", [])

    @property
    def informant_forms(self) -> list[dict[str, Any]]:
        return self.data.get("informant_forms", [])

    @property
    def norms_region(self) -> str | None:
        return self.data.get("norms_region")

    def get_norms(self) -> dict[str, Any]:
        norms = self.data.get("norms")
        if norms is not None:
            return norms
        norms_file = self.data.get("norms_file")
        if norms_file:
            norms_path = self._package_dir / norms_file
            if norms_path.is_file():
                with norms_path.open(encoding="utf-8") as handle:
                    return json.load(handle)
            logger.warning("norms_file %s not found for instrument %s", norms_file, self.slug)
        return {}

    def get_items(self) -> list[dict[str, Any]]:
        items = self.data.get("items")
        if items is not None:
            return items

        items_file = self.data.get("items_file")
        if items_file:
            items_path = self._package_dir / items_file
            if items_path.is_file():
                with items_path.open(encoding="utf-8") as handle:
                    return json.load(handle)
            logger.warning("items_file %s not found for instrument %s", items_file, self.slug)
        return []

    def get_module_config(self, module_slug: str) -> dict[str, Any]:
        if module_slug in self.modules:
            return self.modules[module_slug]
        legacy = self.data.get("legacy_modules") or {}
        if module_slug in legacy:
            entry = dict(legacy[module_slug])
            entry.setdefault("id", module_slug)
            entry.setdefault("deprecated", True)
            return entry
        raise KeyError(f"Module '{module_slug}' not found in package '{self.slug}'")

    def is_legacy_module(self, module_slug: str) -> bool:
        if module_slug in self.modules:
            return bool(self.modules[module_slug].get("deprecated"))
        return module_slug in (self.data.get("legacy_modules") or {})

    def get_module_items(self, module_slug: str) -> list[dict[str, Any]]:
        mod = self.get_module_config(module_slug)
        inline = mod.get("items")
        if inline is not None:
            return inline
        items_file = mod.get("items_file")
        if items_file:
            items_path = self._package_dir / items_file
            if items_path.is_file():
                with items_path.open(encoding="utf-8") as handle:
                    return json.load(handle)
            logger.warning("items_file %s not found for module %s", items_file, module_slug)
        return []

    def list_battery_modules(self) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for slug, mod in self.modules.items():
            entries.append(
                {
                    "slug": slug,
                    "title": mod.get("title", slug),
                    "module_kind": mod.get("module_kind", "generic"),
                    "domain": mod.get("domain", slug),
                    "filler": mod.get("filler", "clinician"),
                    "item_count": mod.get("item_count") or len(self.get_module_items(slug)),
                    "categories": mod.get("categories", []),
                }
            )
        return entries

    def public_module_form(self, module_slug: str) -> dict[str, Any]:
        mod = self.get_module_config(module_slug)
        items = self.get_module_items(module_slug)
        return {
            "subform_slug": module_slug,
            "title": mod.get("title", module_slug),
            "module_kind": mod.get("module_kind", "generic"),
            "domain": mod.get("domain"),
            "categories": mod.get("categories", []),
            "classifications": self.data.get("classifications", {}).get(
                mod.get("module_kind", "generic"), []
            ),
            "phonological_processes": self.data.get("phonological_processes", []),
            "target_syllables": mod.get("target_syllables"),
            "scale": mod.get("scale") or self.scale,
            "input_type": mod.get("input_type", "scale"),
            "administration_rules": self.scoring.get("administration_rules") or None,
            "items": [
                {
                    "id": item["id"],
                    "text": item.get("text", ""),
                    "target": item.get("target"),
                    "category": item.get("category"),
                    "category_title": item.get("category_title"),
                    "stimulus_type": item.get("stimulus_type", "word"),
                    "input_type": item.get("input_type") or mod.get("input_type", "scale"),
                    "options": item.get("options", []),
                    "age_start_months": item.get("age_start_months"),
                    "age_end_months": item.get("age_end_months"),
                    "material": item.get("material"),
                    "examiner_instructions": item.get("examiner_instructions"),
                    "section": item.get("section"),
                    "response_type": item.get("response_type", "developmental"),
                }
                for item in items
            ],
            "filler": mod.get("filler", "clinician"),
        }

    def get_items_page(
        self,
        *,
        page: int = 1,
        page_size: int = 50,
        section: str | None = None,
        module: str | None = None,
    ) -> dict[str, Any]:
        if module and module in self.modules:
            mod = self.modules[module]
            items = mod.get("items") or self.get_module_items(module)
        else:
            items = self.get_items()
        if section:
            items = [item for item in items if item.get("section") == section]
        if module and not self.modules.get(module):
            items = [
                item
                for item in items
                if item.get("module") == module or item.get("domain") == module
            ]

        total = len(items)
        start = max(page - 1, 0) * page_size
        end = start + page_size
        page_items = items[start:end]

        return {
            "items": self.public_items_payload(page_items),
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": max(1, (total + page_size - 1) // page_size) if total else 1,
        }

    def public_manifest(self) -> dict[str, Any]:
        manifest = {
            "package_id": self.package_id,
            "instrument_slug": self.slug,
            "instrument_title": self.instrument_title,
            "version": self.version,
            "archetype": self.archetype,
            "scale": self.scale,
            "domains": self.domains,
            "item_count": len(self.get_items()),
            "scoring_engine": self.scoring.get("engine"),
            "report": {
                "template_id": self.report.get("template_id"),
                "sections": self.report.get("sections", []),
            },
        }
        if self.subtests:
            manifest["subtests"] = self.subtests
        if self.modules:
            manifest["modules"] = [
                {
                    "id": k,
                    "title": v.get("title", k),
                    "item_count": v.get("item_count") or len(self.get_module_items(k)),
                    "module_kind": v.get("module_kind"),
                    "domain": v.get("domain"),
                }
                for k, v in self.modules.items()
            ]
        if self.data.get("phonological_processes"):
            manifest["phonological_processes"] = self.data["phonological_processes"]
        if self.data.get("classifications"):
            manifest["classifications"] = self.data["classifications"]
        if self.informant_forms:
            manifest["informant_forms"] = self.informant_forms
        manifest["requires_competency_ack"] = self.data.get("requires_competency_ack", False)
        manifest["supports_multi_session"] = self.data.get("supports_multi_session", False)
        manifest["has_norms"] = bool(self.get_norms()) or bool(self.data.get("norms_file"))
        from app.services.norms_status import summarize_norms_status

        manifest["norms_status"] = summarize_norms_status(self)
        if self.norms_region:
            manifest["norms_region"] = self.norms_region
        elif self.data.get("norms_file"):
            manifest["norms_region"] = str(self.get_norms().get("region") or "BR")
        return manifest

    def public_items_payload(self, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "id": item["id"],
                "domain": item.get("domain"),
                "text": item["text"],
                "section": item.get("section"),
                "module": item.get("module"),
            }
            for item in items
        ]

    @property
    def _package_dir(self) -> Path:
        settings = get_settings()
        configured_root = settings.instrument_packages_root
        if configured_root:
            override = Path(configured_root) / self.slug / "manifest.json"
            if override.is_file():
                return override.parent
        data_path = DATA_PACKAGES_ROOT / self.slug / "manifest.json"
        if data_path.is_file():
            return data_path.parent
        return DEFAULT_SAMPLES_ROOT / self.slug


def _resolve_manifest_path(slug: str) -> Path:
    settings = get_settings()
    configured_root = settings.instrument_packages_root
    if configured_root:
        override = Path(configured_root) / slug / "manifest.json"
        if override.is_file():
            return override

    data_path = DATA_PACKAGES_ROOT / slug / "manifest.json"
    if data_path.is_file():
        return data_path

    sample_path = DEFAULT_SAMPLES_ROOT / slug / "manifest.json"
    if sample_path.is_file():
        return sample_path

    raise FileNotFoundError(f"Instrument package manifest not found for slug '{slug}'")


def _load_package(slug: str) -> InstrumentContentPackage:
    manifest_path = _resolve_manifest_path(slug)
    with manifest_path.open(encoding="utf-8") as handle:
        data = json.load(handle)

    data_dir = manifest_path.parent
    items_file = data.get("items_file")
    if items_file and "items" not in data:
        items_path = data_dir / items_file
        if items_path.is_file():
            with items_path.open(encoding="utf-8") as handle:
                data["items"] = json.load(handle)

    for mod_slug, mod in list(data.get("modules", {}).items()):
        mod_items_file = mod.get("items_file")
        if mod_items_file and "items" not in mod:
            mod_items_path = data_dir / mod_items_file
            if mod_items_path.is_file():
                with mod_items_path.open(encoding="utf-8") as handle:
                    mod["items"] = json.load(handle)

    norms_file = data.get("norms_file")
    if norms_file and "norms" not in data:
        norms_path = data_dir / norms_file
        if norms_path.is_file():
            with norms_path.open(encoding="utf-8") as handle:
                data["norms"] = json.load(handle)

    return InstrumentContentPackage(slug, data)


@lru_cache(maxsize=32)
def get_instrument_content_package(slug: str) -> InstrumentContentPackage:
    return _load_package(slug)
