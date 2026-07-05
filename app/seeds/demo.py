"""Development seed — creates demo professional and sample patients."""

import asyncio
from datetime import date, timedelta

from sqlalchemy import select

from app.core.constants import AVATAR_COLORS, CLINICAL_DOMAIN_CATALOG
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, engine
from app.models.assessment import ProtocolCatalog
from app.models.caregiver import Caregiver
from app.models.goal import ClinicalDomainSnapshot, Goal
from app.models.patient import Patient
from app.models.professional import Professional
from app.seeds.protocols import PROTOCOLS
from app.services.timeline import create_timeline_event


async def seed_protocols(session) -> None:
    for p in PROTOCOLS:
        existing = await session.get(ProtocolCatalog, p["id"])
        if not existing:
            session.add(ProtocolCatalog(**p))


async def seed_demo(session) -> None:
    result = await session.execute(
        select(Professional).where(Professional.email == "admin@admin.com")
    )
    if result.scalar_one_or_none():
        return

    professional = Professional(
        email="admin@admin.com",
        password_hash=hash_password("admin123"),
        name="Dra. Camila Rocha",
        specialty_key="fono",
        specialty="Fonoaudiologia",
        council="CRFa 2-12345",
        phone="(11) 98888-1010",
        avatar_color="oklch(0.58 0.12 205)",
        subscription_status="active",
    )
    session.add(professional)
    await session.flush()

    names = [
        ("João Silva", ["tea"], "ativo"),
        ("Maria Oliveira", ["linguagem"], "ativo"),
        ("Pedro Santos", ["apraxia"], "avaliacao"),
        ("Ana Souza", ["dislexia"], "ativo"),
        ("Lucas Costa", ["outros"], "pausado"),
    ]
    for i, (name, diags, status) in enumerate(names):
        birth = date.today().replace(year=date.today().year - (5 + i))
        patient = Patient(
            professional_id=professional.id,
            name=name,
            birth_date=birth,
            diagnosis_keys=diags,
            status=status,
            start_date=date.today() - timedelta(days=90 + i * 10),
            avatar_color=AVATAR_COLORS[i % len(AVATAR_COLORS)],
        )
        session.add(patient)
        await session.flush()
        session.add(
            Caregiver(
                patient_id=patient.id,
                name=f"Responsável {name.split()[0]}",
                relation="Mãe",
                phone="(11) 98888-1010",
                is_primary=True,
            )
        )
        session.add(
            Goal(
                patient_id=patient.id,
                professional_id=professional.id,
                title="Aumentar vocabulário expressivo",
                area="Linguagem",
                progress=60 + i * 5,
                start_date=date.today() - timedelta(days=30),
                status="Em andamento",
            )
        )
        for j, domain in enumerate(CLINICAL_DOMAIN_CATALOG[:4]):
            for k in range(4):
                session.add(
                    ClinicalDomainSnapshot(
                        patient_id=patient.id,
                        key=domain["key"],
                        label=domain["label"],
                        score=40 + i * 3 + j * 5 + k * 4,
                        recorded_at=date.today() - timedelta(days=30 - k * 7),
                    )
                )
        await create_timeline_event(
            session,
            patient_id=patient.id,
            professional_id=professional.id,
            event_type="meta",
            title="Paciente cadastrado",
            description="Início do acompanhamento na clínica",
        )


async def run_seed() -> None:
    async with AsyncSessionLocal() as session:
        from app.services.plan_catalog_seed import seed_plan_catalog

        await seed_protocols(session)
        await seed_plan_catalog(session)
        await seed_demo(session)
        await session.commit()
    await engine.dispose()
    print("Seed concluído.")


if __name__ == "__main__":
    asyncio.run(run_seed())
