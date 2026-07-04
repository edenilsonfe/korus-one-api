from datetime import datetime

from app.schemas.common import CamelModel


class WhatsAppMessageLogItem(CamelModel):
    id: str
    created_at: datetime
    notification_type: str
    event_label: str
    recipient_name: str | None = None
    recipient_phone: str | None = None
    template_name: str | None = None
    status: str
    status_label: str
    delivery_seconds: int | None = None
    last_error: str | None = None
    is_test: bool = False


class WhatsAppMessageLogsResponse(CamelModel):
    items: list[WhatsAppMessageLogItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class WhatsAppMessageLogsStatsResponse(CamelModel):
    period_days: int = 30
    sent: int = 0
    delivered: int = 0
    failed: int = 0
    no_phone: int = 0
    total: int = 0
