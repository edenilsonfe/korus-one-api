"""Schemas for the unified AI assistant (clínico + gestão)."""

from datetime import date, datetime
from typing import List, Literal, Optional

from app.schemas.common import CamelModel


class ChatMetadata(CamelModel):
    tools_used: List[str] = []
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    queried_at: datetime


class ChatResponse(CamelModel):
    reply: str
    metadata: ChatMetadata
    suggestions: Optional[List[str]] = None