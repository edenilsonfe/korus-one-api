from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.utils import utcnow
from app.models.timeline import TimelineEvent


async def create_timeline_event(
    db: AsyncSession,
    *,
    patient_id: UUID,
    professional_id: UUID,
    event_type: str,
    title: str,
    description: str = "",
    source_id: UUID | None = None,
    date: datetime | None = None,
) -> TimelineEvent:
    event = TimelineEvent(
        patient_id=patient_id,
        professional_id=professional_id,
        type=event_type,
        title=title,
        description=description,
        date=date or utcnow(),
        source_id=source_id,
    )
    db.add(event)
    return event
