from dataclasses import dataclass, field
from typing import Any


@dataclass
class WhatsAppSendResult:
    provider: str
    provider_message_id: str | None = None
    status: str = "sent"
    payload: dict[str, Any] = field(default_factory=dict)
