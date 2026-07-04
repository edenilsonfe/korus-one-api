"""Seed the commercial billing plan catalog idempotently."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.billing import Plan

COMMERCIAL_PLAN_SEEDS: list[dict[str, Any]] = [
    {
        "slug": "korusone_pro_monthly",
        "name": "KorusOne Pro",
        "description": "Pacientes ilimitados, IA clínica e relatórios automáticos.",
        "limits": {},
        "price_cents": 9700,
        "currency": "BRL",
        "billing_interval": "monthly",
        "features": [
            "Pacientes ilimitados",
            "Prontuário e agenda completos",
            "IA clínica e relatórios",
            "WhatsApp e notificações",
        ],
        "badge": None,
        "highlighted": True,
        "display_order": 1,
        "is_active": True,
    },
    {
        "slug": "korusone_pro_yearly",
        "name": "korusone Pro",
        "description": "Pacientes ilimitados, IA clínica e relatórios automáticos — cobrança anual.",
        "limits": {},
        "price_cents": 97000,
        "currency": "BRL",
        "billing_interval": "yearly",
        "features": [
            "Pacientes ilimitados",
            "Prontuário e agenda completos",
            "IA clínica e relatórios",
            "WhatsApp e notificações",
            "Economia de ~2 meses no plano anual",
        ],
        "badge": "Melhor valor",
        "highlighted": True,
        "display_order": 2,
        "is_active": True,
    },
]


async def seed_plan_catalog(session: AsyncSession) -> None:
    for seed in COMMERCIAL_PLAN_SEEDS:
        existing = await session.execute(select(Plan).where(Plan.slug == seed["slug"]))
        if existing.scalar_one_or_none():
            continue
        session.add(Plan(**seed))
