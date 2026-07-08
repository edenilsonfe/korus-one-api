"""Heuristics to detect colloquial or compound assistant queries.

Used for logging/telemetry to understand where the model fails to call tools.
Adapted from myclinic-back management_assistant/query_heuristics.py to the
Korus One domain (single professional practice, no branches).
"""

from __future__ import annotations

import unicodedata

COLLOQUIAL_PHRASES = (
    "como está",
    "como esta",
    "como andam",
    "como anda",
    "panorama",
    "visão geral",
    "visao geral",
    "me dá um resumo",
    "me da um resumo",
    "me mostre um resumo",
    "resumo geral",
    "números gerais",
    "numeros gerais",
    "situação geral",
    "situacao geral",
    "como está a clínica",
    "como esta a clinica",
    "como está minha clínica",
    "como esta minha clinica",
    "como está minha prática",
    "como esta minha pratica",
    "como está o consultório",
    "como esta o consultorio",
)

COMPOUND_CONNECTORS = (
    " versus ",
    " vs ",
    " vs. ",
    " e também ",
    " além de ",
    " comparado ",
    " comparar ",
)

SESSION_TERMS = ("sessão", "sessao", "sessões", "sessoes", "atendimento", "atendimentos", "consulta", "consultas")
STATUS_TERMS = ("falta", "faltas", "faltou", "no-show", "no show", "cancelad", "concluíd", "concluid", "confirmad", "pendente")
ENTITY_TERMS = ("paciente", "pacientes", "criança", "criancas")
CLINICAL_TERMS = ("evolução", "evolucao", "meta", "metas", "avaliação", "avaliacao", "instrumento", "prontuário", "prontuario")


def _normalize(text: str) -> str:
    lowered = text.lower().strip()
    normalized = unicodedata.normalize("NFD", lowered)
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")


def _has_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def is_colloquial(query: str) -> bool:
    normalized = _normalize(query)
    return any(phrase in normalized for phrase in COLLOQUIAL_PHRASES)


def is_compound(query: str) -> bool:
    normalized = _normalize(query)
    if any(connector in normalized for connector in COMPOUND_CONNECTORS):
        return True
    flags = (
        _has_any(normalized, SESSION_TERMS),
        _has_any(normalized, STATUS_TERMS),
        _has_any(normalized, ENTITY_TERMS),
        _has_any(normalized, CLINICAL_TERMS),
    )
    if sum(flags) >= 2:
        return True
    return False


def classify_query(query: str) -> str:
    """Return 'colloquial', 'compound', or 'none'."""
    if is_colloquial(query):
        return "colloquial"
    if is_compound(query):
        return "compound"
    return "none"
