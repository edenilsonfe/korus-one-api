"""Map appointment PATCH changes to WhatsApp queue event names."""


def resolve_appointment_update_whatsapp_event(
    *,
    old_status: str,
    new_status: str,
    status_changed: bool,
    date_or_time_changed: bool,
) -> str | None:
    """Which WhatsApp queue event to fire after PATCH (or None)."""
    if status_changed and new_status == "cancelado" and old_status != "cancelado":
        return "cancelled"
    if date_or_time_changed and new_status != "cancelado":
        return "rescheduled"
    if status_changed and new_status == "confirmado" and old_status != "confirmado":
        return "confirmation"
    return None
