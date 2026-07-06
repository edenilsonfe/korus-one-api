"""PDF report export for generic battery assessments."""

from __future__ import annotations

import io
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from app.schemas.battery import BatteryResponse
from app.services.instrument_content_package import InstrumentContentPackage


def export_battery_pdf(battery: BatteryResponse, package: InstrumentContentPackage) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story: list[Any] = [
        Paragraph("KorusOne", styles["Title"]),
        Paragraph(package.instrument_title, styles["Heading1"]),
        Spacer(1, 12),
        Paragraph(f"Paciente: {battery.patient_name or battery.patient_id}", styles["Normal"]),
        Paragraph(f"Data: {battery.created_at.date().isoformat()}", styles["Normal"]),
    ]
    if battery.duration_minutes:
        story.append(Paragraph(f"Duração: {battery.duration_minutes} minutos", styles["Normal"]))
    story.append(Spacer(1, 16))

    if package.scoring.get("engine") == "observational_domains":
        story.append(Paragraph("Objetivo", styles["Heading2"]))
        story.append(
            Paragraph(
                "Avaliação observacional de comunicação, linguagem e aspectos cognitivos.",
                styles["Normal"],
            )
        )
        story.append(Spacer(1, 12))

    story.append(Paragraph("Resultados por módulo", styles["Heading2"]))

    scores = battery.scores or {}
    for slug, domain_score in (scores.get("domains") or {}).items():
        if isinstance(domain_score, dict):
            story.append(Paragraph(domain_score.get("summary", slug), styles["Normal"]))
            if domain_score.get("module_kind") == "phonology":
                for proc in domain_score.get("processes", [])[:10]:
                    persistent = " — persistente" if proc.get("persistent") else ""
                    story.append(
                        Paragraph(
                            f"• {proc.get('label')}: {proc.get('count')} ocorrências{persistent}",
                            styles["Normal"],
                        )
                    )
            if domain_score.get("module_kind") == "vocabulary":
                for cat in domain_score.get("categories", []):
                    story.append(
                        Paragraph(
                            f"• {cat.get('title')}: {cat.get('percentage')}% DVU",
                            styles["Normal"],
                        )
                    )
            if domain_score.get("module_kind") == "observational":
                level = domain_score.get("level", "unknown")
                story.append(
                    Paragraph(
                        f"• Classificação: {level} — {domain_score.get('percentage', 0)}%",
                        styles["Normal"],
                    )
                )
            story.append(Spacer(1, 8))

    clinical_conclusion = scores.get("clinical_conclusion") or scores.get("clinicalConclusion")
    if clinical_conclusion:
        story.append(Spacer(1, 12))
        story.append(Paragraph("Conclusão clínica", styles["Heading2"]))
        story.append(Paragraph(str(clinical_conclusion), styles["Normal"]))

    story.append(Spacer(1, 12))
    story.append(Paragraph("Resumo", styles["Heading2"]))
    story.append(
        Paragraph(
            scores.get("interpretation") or scores.get("summary") or "Avaliação concluída.",
            styles["Normal"],
        )
    )
    story.append(Spacer(1, 24))
    story.append(Paragraph("Assinatura do profissional: _________________________", styles["Normal"]))

    doc.build(story)
    return buffer.getvalue()
