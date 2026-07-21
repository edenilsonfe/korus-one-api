"""Validation helpers for patient prontuario attachment uploads."""

from __future__ import annotations

import re

from fastapi import HTTPException, status

# Matches the patient hub accept list, minus SVG (XSS when rendered as <img>).
ATTACHMENT_ALLOWED_CONTENT_TYPES: frozenset[str] = frozenset(
    {
        "application/pdf",
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "video/mp4",
        "video/webm",
        "video/quicktime",
        "audio/mpeg",
        "audio/mp4",
        "audio/wav",
        "audio/x-wav",
        "audio/webm",
        "audio/ogg",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
)

ATTACHMENT_ALLOWED_CATEGORIES: frozenset[str] = frozenset(
    {"video", "audio", "foto", "relatorio"}
)

_SAFE_FILENAME_RE = re.compile(r"[^\w.\- ()\[\]]+", re.UNICODE)

# Declared content-type → accepted sniffed families (None = no reliable magic).
_SNIFF_COMPAT: dict[str, frozenset[str] | None] = {
    "application/pdf": frozenset({"application/pdf"}),
    "image/jpeg": frozenset({"image/jpeg"}),
    "image/png": frozenset({"image/png"}),
    "image/gif": frozenset({"image/gif"}),
    "image/webp": frozenset({"image/webp"}),
    "application/msword": frozenset({"application/msword"}),
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": frozenset(
        {"application/zip"}
    ),
    "video/mp4": frozenset({"video/mp4"}),
    "video/quicktime": frozenset({"video/mp4"}),
    "audio/mp4": frozenset({"video/mp4"}),
    "video/webm": frozenset({"video/webm"}),
    "audio/webm": frozenset({"video/webm"}),
    "audio/mpeg": frozenset({"audio/mpeg"}),
    "audio/ogg": frozenset({"audio/ogg"}),
    "audio/wav": frozenset({"audio/wav"}),
    "audio/x-wav": frozenset({"audio/wav"}),
}


def normalize_content_type(content_type: str | None) -> str:
    return (content_type or "").split(";", 1)[0].strip().lower()


def sanitize_filename(name: str | None) -> str:
    raw = (name or "upload").replace("\\", "/")
    base = raw.rsplit("/", 1)[-1].strip().strip(".")
    if not base:
        base = "upload"
    base = re.sub(r"[\x00-\x1f\x7f]", "", base)
    base = _SAFE_FILENAME_RE.sub("_", base).strip("._") or "upload"
    return base[:180]


def sniff_content_type(body: bytes) -> str | None:
    if body.startswith(b"%PDF"):
        return "application/pdf"
    if body.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if body.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if body.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(body) >= 12 and body[:4] == b"RIFF" and body[8:12] == b"WEBP":
        return "image/webp"
    if body.startswith(b"PK\x03\x04"):
        return "application/zip"
    if body.startswith(b"\xd0\xcf\x11\xe0"):
        return "application/msword"
    if len(body) >= 12 and body[4:8] == b"ftyp":
        return "video/mp4"
    if body.startswith(b"\x1aE\xdf\xa3"):
        return "video/webm"
    if body.startswith(b"OggS"):
        return "audio/ogg"
    if len(body) >= 12 and body[:4] == b"RIFF" and body[8:12] == b"WAVE":
        return "audio/wav"
    if body.startswith(b"ID3") or (len(body) >= 2 and body[0] == 0xFF and body[1] & 0xE0 == 0xE0):
        return "audio/mpeg"
    return None


def validate_attachment_category(category: str) -> str:
    if category not in ATTACHMENT_ALLOWED_CATEGORIES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Categoria de anexo inválida.",
        )
    return category


def validate_attachment_upload(
    *,
    content_type: str | None,
    filename: str | None,
    body: bytes,
) -> tuple[str, str]:
    """Return (normalized_content_type, safe_filename) or raise HTTPException."""
    if not body:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio não é permitido.",
        )

    declared = normalize_content_type(content_type)
    if declared not in ATTACHMENT_ALLOWED_CONTENT_TYPES:
        allowed = ", ".join(sorted(ATTACHMENT_ALLOWED_CONTENT_TYPES))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo de arquivo não suportado. Permitidos: {allowed}.",
        )

    safe_name = sanitize_filename(filename)
    sniffed = sniff_content_type(body)
    expected = _SNIFF_COMPAT.get(declared)
    if expected is not None:
        if sniffed is None or sniffed not in expected:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Conteúdo do arquivo não corresponde ao tipo declarado.",
            )

    return declared, safe_name
