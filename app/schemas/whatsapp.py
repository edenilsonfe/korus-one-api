from datetime import datetime

from pydantic import Field

from app.schemas.common import CamelModel


class WhatsAppConnectionStatus(CamelModel):
    status: str
    waba_id: str | None = None
    phone_number_id: str | None = None
    display_phone_number: str | None = None
    verified_name: str | None = None
    last_error: str | None = None
    connected_at: datetime | None = None
    evolution_instance_name: str | None = None
    qrcode_base64: str | None = None
    connection_state: str | None = None


class WhatsAppStatusResponse(CamelModel):
    provider: str
    embedded_signup_enabled: bool = False
    connection: WhatsAppConnectionStatus | None = None
    can_send: bool = False


class WhatsAppConnectResponse(CamelModel):
    provider: str
    connection: WhatsAppConnectionStatus
    qrcode_base64: str | None = None
    connection_state: str | None = None
    can_send: bool = False


class WhatsAppUsageResponse(CamelModel):
    month: str
    used: int
    limit: int = 0
    remaining: int = 0
