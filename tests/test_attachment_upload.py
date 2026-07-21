"""Unit tests for attachment upload validation helpers."""

import pytest
from fastapi import HTTPException

from app.services.attachment_upload import (
    assert_declared_matches_sniff,
    sanitize_filename,
    sniff_content_type,
    validate_attachment_upload,
)


def test_sanitize_filename_strips_path_and_controls():
    assert sanitize_filename("../../etc/passwd.pdf") == "passwd.pdf"
    assert sanitize_filename("a\\b\\c.docx") == "c.docx"
    assert sanitize_filename("relatório.pdf") == "relatório.pdf"
    assert sanitize_filename("bad\x00name.pdf") == "badname.pdf"
    assert sanitize_filename("") == "upload"


def test_sniff_pdf_png_jpeg():
    assert sniff_content_type(b"%PDF-1.7\n...") == "application/pdf"
    assert sniff_content_type(b"\x89PNG\r\n\x1a\nxxxx") == "image/png"
    assert sniff_content_type(b"\xff\xd8\xff\xe0xxxx") == "image/jpeg"


def test_validate_rejects_svg_and_empty():
    with pytest.raises(HTTPException) as exc:
        validate_attachment_upload(
            content_type="image/svg+xml",
            filename="x.svg",
            body=b"<svg></svg>",
        )
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        validate_attachment_upload(
            content_type="application/pdf",
            filename="x.pdf",
            body=b"",
        )
    assert exc.value.status_code == 400


def test_validate_accepts_matching_pdf():
    ctype, name = validate_attachment_upload(
        content_type="application/pdf; charset=binary",
        filename="laudo.pdf",
        body=b"%PDF-1.4\ndata",
    )
    assert ctype == "application/pdf"
    assert name == "laudo.pdf"


def test_assert_declared_matches_sniff_rejects_mismatch():
    assert_declared_matches_sniff("image/png", b"\x89PNG\r\n\x1a\nxxxx")
    with pytest.raises(HTTPException) as exc:
        assert_declared_matches_sniff("image/png", b"%PDF-1.4\ndata")
    assert exc.value.status_code == 400
