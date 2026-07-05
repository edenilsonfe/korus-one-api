"""Export AI reports to PDF, DOCX, TXT and MD."""

from __future__ import annotations

import io
from datetime import date

from docx import Document
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

REPORT_TYPE_LABELS = {
    "clinico": "Relatório Clínico",
    "escolar": "Relatório Escolar",
    "pais": "Relatório para Pais",
    "evolutivo": "Relatório Evolutivo",
}


def _header_lines(report_type: str, patient_name: str, report_date: date) -> list[str]:
    type_label = REPORT_TYPE_LABELS.get(report_type, report_type)
    return [
        "KorusOne",
        type_label,
        f"Paciente: {patient_name}",
        f"Data: {report_date.isoformat()}",
        "",
    ]


def export_txt(report_type: str, patient_name: str, report_date: date, content: str) -> bytes:
    lines = _header_lines(report_type, patient_name, report_date)
    lines.append(content)
    return "\n".join(lines).encode("utf-8")


def export_md(report_type: str, patient_name: str, report_date: date, content: str) -> bytes:
    type_label = REPORT_TYPE_LABELS.get(report_type, report_type)
    body = (
        f"# {type_label}\n\n"
        f"**Paciente:** {patient_name}  \n"
        f"**Data:** {report_date.isoformat()}\n\n"
        f"---\n\n"
        f"{content}\n"
    )
    return body.encode("utf-8")


def export_docx(report_type: str, patient_name: str, report_date: date, content: str) -> bytes:
    doc = Document()
    doc.add_heading("KorusOne", level=1)
    type_label = REPORT_TYPE_LABELS.get(report_type, report_type)
    doc.add_heading(type_label, level=2)
    doc.add_paragraph(f"Paciente: {patient_name}")
    doc.add_paragraph(f"Data: {report_date.isoformat()}")
    doc.add_paragraph("")
    for paragraph in content.split("\n"):
        doc.add_paragraph(paragraph)
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def export_pdf(report_type: str, patient_name: str, report_date: date, content: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    type_label = REPORT_TYPE_LABELS.get(report_type, report_type)
    story = [
        Paragraph("KorusOne", styles["Title"]),
        Paragraph(type_label, styles["Heading2"]),
        Paragraph(f"Paciente: {patient_name}", styles["Normal"]),
        Paragraph(f"Data: {report_date.isoformat()}", styles["Normal"]),
        Spacer(1, 12),
    ]
    for paragraph in content.split("\n"):
        if paragraph.strip():
            story.append(Paragraph(paragraph.replace("&", "&amp;").replace("<", "&lt;"), styles["Normal"]))
        else:
            story.append(Spacer(1, 6))
    doc.build(story)
    return buffer.getvalue()


def export_report(
    format: str,
    report_type: str,
    patient_name: str,
    report_date: date,
    content: str,
) -> tuple[bytes, str, str]:
    """Return (bytes, media_type, filename_suffix)."""
    if format in ("txt", "md"):
        exporter = export_txt if format == "txt" else export_md
        media = "text/plain; charset=utf-8" if format == "txt" else "text/markdown; charset=utf-8"
        return exporter(report_type, patient_name, report_date, content), media, format
    if format == "docx":
        return (
            export_docx(report_type, patient_name, report_date, content),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "docx",
        )
    if format == "pdf":
        return (
            export_pdf(report_type, patient_name, report_date, content),
            "application/pdf",
            "pdf",
        )
    raise ValueError(f"Formato não suportado: {format}")
