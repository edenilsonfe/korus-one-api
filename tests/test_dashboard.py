from datetime import date, datetime, time

from app.services.dashboard import build_suggestions, derive_agenda_status

NOW = datetime(2026, 7, 9, 14, 0)
TODAY = date(2026, 7, 9)


def test_status_confirmado_futuro_mantido():
    assert derive_agenda_status("confirmado", TODAY, time(15, 0), False, NOW) == "confirmado"


def test_status_pendente_futuro_mantido():
    assert derive_agenda_status("pendente", TODAY, time(15, 0), False, NOW) == "pendente"


def test_horario_passado_sem_sessao_vira_evolucao_pendente():
    assert derive_agenda_status("confirmado", TODAY, time(10, 0), False, NOW) == "evolucao_pendente"
    assert derive_agenda_status("pendente", TODAY, time(10, 0), False, NOW) == "evolucao_pendente"


def test_horario_passado_com_sessao_mantem_status():
    assert derive_agenda_status("confirmado", TODAY, time(10, 0), True, NOW) == "confirmado"


def test_status_cancelado_nao_derivado():
    assert derive_agenda_status("cancelado", TODAY, time(10, 0), False, NOW) == "cancelado"


def test_suggestions_vazia_sem_pendencias():
    assert (
        build_suggestions(
            {
                "evolutions": 0,
                "reports": 0,
                "sessions": 0,
                "assessmentDrafts": 0,
                "awaitingInformant": 0,
            }
        )
        == []
    )


def test_suggestions_completa_com_ctas():
    result = build_suggestions(
        {
            "evolutions": 2,
            "reports": 1,
            "sessions": 3,
            "assessmentDrafts": 4,
            "awaitingInformant": 1,
        }
    )
    assert [s["id"] for s in result] == [
        "pending-evolutions",
        "pending-assessment-drafts",
        "pending-awaiting-informant",
        "pending-reports",
        "pending-sessions",
    ]
    assert result[0]["ctaTo"] == "/agenda"
    assert result[1]["ctaTo"] == "/avaliacoes?status=draft"
    assert result[2]["ctaTo"] == "/avaliacoes?status=awaiting_informant"
    assert result[3]["ctaTo"] == "/relatorios"
    assert result[4]["ctaTo"] == "/agenda"
    assert "2 evoluções" in result[0]["text"]
    assert "4 avaliações em rascunho" in result[1]["text"]
    assert "1 relatório em rascunho" in result[3]["text"]
