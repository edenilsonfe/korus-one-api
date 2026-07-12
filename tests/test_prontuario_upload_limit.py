"""Regression test for the prontuario attachment upload size cap (413)."""

from unittest.mock import AsyncMock, patch

from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.ext.compiler import compiles

from app.core.config import get_settings


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(_type, _compiler, **_kw):
    return "JSON"


@compiles(ARRAY, "sqlite")
def _compile_array_sqlite(_type, _compiler, **_kw):
    return "JSON"


async def test_upload_over_limit_rejected_and_under_limit_succeeds(api_client, patient, auth_headers):
    max_bytes = get_settings().max_upload_bytes
    oversized = b"x" * (max_bytes + 1)

    with patch("app.api.v1.prontuario.storage_service.upload", new_callable=AsyncMock) as mock_upload:
        resp = await api_client.post(
            f"/api/v1/patients/{patient.id}/attachments",
            files={"file": ("laudo.pdf", oversized, "application/pdf")},
            headers=auth_headers,
        )
        assert resp.status_code == 413
        assert "tamanho máximo" in resp.json()["detail"]
        mock_upload.assert_not_called()

        body = b"conteudo pequeno de laudo"
        resp = await api_client.post(
            f"/api/v1/patients/{patient.id}/attachments",
            files={"file": ("laudo.pdf", body, "application/pdf")},
            headers=auth_headers,
        )
        assert resp.status_code == 201
        assert resp.json()["sizeBytes"] == len(body)
        mock_upload.assert_called_once()
