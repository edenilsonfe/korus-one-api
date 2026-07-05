"""Specialty keys and display labels."""

from typing import Literal

SpecialtyKey = Literal["fono", "to", "psicologia", "fisioterapia"]

SPECIALTY_KEYS: tuple[str, ...] = ("fono", "to", "psicologia", "fisioterapia")

SPECIALTY_LABELS: dict[str, str] = {
    "fono": "Fonoaudiologia",
    "to": "Terapia Ocupacional",
    "psicologia": "Psicologia",
    "fisioterapia": "Fisioterapia",
}


def specialty_label(key: str) -> str:
    return SPECIALTY_LABELS.get(key, key)


def is_valid_specialty_key(key: str) -> bool:
    return key in SPECIALTY_LABELS
