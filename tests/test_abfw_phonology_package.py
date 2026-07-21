"""Smoke: ABFW fonologia serves the updated word lists from app/data/abfw."""

from app.services.instrument_content_package import (
    clear_instrument_content_package_cache,
    get_instrument_content_package,
    _resolve_manifest_path,
)


def test_abfw_phonology_package_loads_updated_words():
    clear_instrument_content_package_cache()
    path = _resolve_manifest_path("abfw")
    assert "instrument_samples" not in str(path).replace("\\", "/")
    assert path.as_posix().endswith("app/data/abfw/manifest.json") or "data/abfw/manifest.json" in path.as_posix()

    package = get_instrument_content_package("abfw")
    assert package.package_id == "abfw-br-v2"

    naming = package.get_module_items("fonologia-nomeacao")
    imitation = package.get_module_items("fonologia-imitacao")
    naming_targets = [str(i.get("target") or i.get("text") or "") for i in naming]
    imitation_targets = [str(i.get("target") or i.get("text") or "") for i in imitation]

    assert len(naming) == 34
    assert len(imitation) == 39
    assert "palhaço" in naming_targets
    assert "peteca" in imitation_targets
    assert "palavra_37" not in imitation_targets
