"""Unit tests for chunked battery evidence upload size cap."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.services.battery_evidence_service import BatteryEvidenceService, EVIDENCE_SIZE_LIMITS


class _ChunkedUploadFile:
    def __init__(
        self,
        data: bytes,
        *,
        content_type: str = "image/jpeg",
        filename: str = "photo.jpg",
    ):
        self._data = data
        self._pos = 0
        self.content_type = content_type
        self.filename = filename

    async def read(self, size: int = -1) -> bytes:
        if self._pos >= len(self._data):
            return b""
        if size < 0:
            chunk = self._data[self._pos :]
        else:
            chunk = self._data[self._pos : self._pos + size]
        self._pos += len(chunk)
        return chunk


def _make_service() -> tuple[BatteryEvidenceService, MagicMock, MagicMock]:
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()

    async def _refresh(obj):
        if getattr(obj, "id", None) is None:
            obj.id = uuid4()
        if getattr(obj, "created_at", None) is None:
            obj.created_at = datetime.now(timezone.utc)

    db.refresh = AsyncMock(side_effect=_refresh)

    service = BatteryEvidenceService(db)
    battery = MagicMock()
    battery.patient_id = uuid4()
    service._load_battery = AsyncMock(return_value=battery)
    return service, db, battery


@pytest.mark.asyncio
async def test_upload_under_limit_calls_storage(monkeypatch):
    monkeypatch.setitem(EVIDENCE_SIZE_LIMITS, "photo", 64)
    service, _db, battery = _make_service()
    body = b"x" * 32
    file = _ChunkedUploadFile(body)

    with patch("app.services.battery_evidence_service.storage_service") as storage:
        storage.make_key.return_value = "patients/key/photo.jpg"
        storage.upload = AsyncMock()
        storage.presigned_url = AsyncMock(return_value="https://example.com/photo.jpg")

        result = await service.upload_evidence(
            uuid4(),
            professional_id=uuid4(),
            file=file,
            kind="photo",
        )

        storage.upload.assert_awaited_once()
        assert storage.upload.await_args.args[1] == body
        assert result["kind"] == "photo"
        assert result["url"] == "https://example.com/photo.jpg"
        storage.make_key.assert_called_once_with(battery.patient_id, "photo.jpg")


@pytest.mark.asyncio
async def test_upload_over_limit_returns_413_and_skips_storage(monkeypatch):
    monkeypatch.setitem(EVIDENCE_SIZE_LIMITS, "photo", 64)
    service, _db, _battery = _make_service()
    file = _ChunkedUploadFile(b"x" * 65)

    with patch("app.services.battery_evidence_service.storage_service") as storage:
        storage.upload = AsyncMock()

        with pytest.raises(HTTPException) as exc_info:
            await service.upload_evidence(
                uuid4(),
                professional_id=uuid4(),
                file=file,
                kind="photo",
            )

        assert exc_info.value.status_code == 413
        assert "excede limite" in exc_info.value.detail
        storage.upload.assert_not_called()
        storage.make_key.assert_not_called()
