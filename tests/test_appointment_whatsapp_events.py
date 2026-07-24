"""PATCH appointment → which WhatsApp event is enqueued."""

from app.services.appointment_whatsapp_events import (
    resolve_appointment_update_whatsapp_event,
)


def test_confirmado_from_pendente_enqueues_confirmation():
    assert (
        resolve_appointment_update_whatsapp_event(
            old_status="pendente",
            new_status="confirmado",
            status_changed=True,
            date_or_time_changed=False,
        )
        == "confirmation"
    )


def test_confirmado_again_is_noop():
    assert (
        resolve_appointment_update_whatsapp_event(
            old_status="confirmado",
            new_status="confirmado",
            status_changed=True,
            date_or_time_changed=False,
        )
        is None
    )


def test_reschedule_wins_over_confirmado():
    assert (
        resolve_appointment_update_whatsapp_event(
            old_status="pendente",
            new_status="confirmado",
            status_changed=True,
            date_or_time_changed=True,
        )
        == "rescheduled"
    )


def test_cancelado_wins():
    assert (
        resolve_appointment_update_whatsapp_event(
            old_status="confirmado",
            new_status="cancelado",
            status_changed=True,
            date_or_time_changed=True,
        )
        == "cancelled"
    )
