import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_SAMPLES_ROOT = Path(__file__).resolve().parent.parent / "data" / "instrument_samples"


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
            items = mod.get("items", [])
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
                {"id": k, "title": v.get("title", k), "item_count": len(v.get("items", []))}
                for k, v in self.modules.items()
            ]
        if self.informant_forms:
            manifest["informant_forms"] = self.informant_forms
        manifest["requires_competency_ack"] = self.data.get("requires_competency_ack", False)
        manifest["supports_multi_session"] = self.data.get("supports_multi_session", False)
        if self.norms_region:
            manifest["norms_region"] = self.norms_region
            manifest["has_norms"] = bool(self.get_norms())
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
        return DEFAULT_SAMPLES_ROOT / self.slug


def _resolve_manifest_path(slug: str) -> Path:
    settings = get_settings()
    configured_root = settings.instrument_packages_root
    if configured_root:
        override = Path(configured_root) / slug / "manifest.json"
        if override.is_file():
            return override

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
