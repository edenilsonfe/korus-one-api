from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_professional, get_patient_for_professional
from app.core.utils import goal_status_from_progress, utcnow
from app.db.session import get_db
from app.models.assessment import Assessment, ASSESSMENT_STATUS_COMPLETED, ProtocolCatalog
from app.models.goal import ClinicalDomainSnapshot, Goal
from app.models.patient import Patient
from app.models.professional import Professional
from app.schemas.clinical import AssessmentCreate, GoalCreate, GoalUpdate, ProtocolResponse
from app.schemas.common import PaginatedResponse
from app.schemas.patient import AssessmentResponse, GoalResponse
from app.services.assessment_scoring import (
    build_assessment_from_scores,
    get_protocol_scoring_mode,
    score_manifest_protocol,
)
from app.services.patient import build_clinical_domains
from app.services.timeline import create_timeline_event

def _assessment_response(
    assessment: Assessment,
    protocol_name: str,
    professional_name: str,
    *,
    patient: Patient | None = None,
) -> AssessmentResponse:
    return AssessmentResponse(
        id=str(assessment.id),
        protocol=protocol_name,
        protocol_id=assessment.protocol_id,
        date=assessment.date.isoformat(),
        professional=professional_name,
        result=assessment.result,
        percentage=assessment.percentage,
        interpretation=assessment.interpretation,
        fields=assessment.fields or [],
        patient_id=str(patient.id) if patient else None,
        patient_name=patient.name if patient else None,
        avatar_color=patient.avatar_color if patient else None,
        answers=assessment.answers or {},
        scores=assessment.scores,
        status=assessment.status,
        informant=assessment.informant,
    )


router = APIRouter(tags=["clinical"])


@router.get("/protocols", response_model=list[ProtocolResponse])
async def list_protocols(
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(ProtocolCatalog).order_by(ProtocolCatalog.name.asc()))
    protocols = result.scalars().all()
    responses = []
    for p in protocols:
        stats = await db.execute(
            select(func.count(), func.avg(Assessment.percentage), func.max(Assessment.date))
            .join(Patient, Assessment.patient_id == Patient.id)
            .where(
                Assessment.protocol_id == p.id,
                Patient.professional_id == professional.id,
                Assessment.status == ASSESSMENT_STATUS_COMPLETED,
            )
        )
        count, avg_result, last_applied = stats.one()
        responses.append(
            ProtocolResponse(
                id=p.id,
                name=p.name,
                full_name=p.full_name,
                description=p.description,
                age_range=p.age_range,
                fields=[{"key": f.get("key", f["label"].lower().replace(" ", "_")), "label": f["label"]} for f in (p.field_templates or [])],
                applications=count or 0,
                avg_result=float(avg_result or 0),
                last_applied=last_applied.isoformat() if last_applied else None,
                scoring_mode=get_protocol_scoring_mode(p.id),
            )
        )
    return responses


@router.get("/protocols/{protocol_id}", response_model=ProtocolResponse)
async def get_protocol(protocol_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ProtocolCatalog).where(ProtocolCatalog.id == protocol_id))
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado")
    return ProtocolResponse(
        id=p.id,
        name=p.name,
        full_name=p.full_name,
        description=p.description,
        age_range=p.age_range,
        fields=[{"key": f.get("key", f["label"].lower().replace(" ", "_")), "label": f["label"]} for f in (p.field_templates or [])],
        scoring_mode=get_protocol_scoring_mode(p.id),
    )


@router.get("/assessments", response_model=PaginatedResponse[AssessmentResponse])
async def list_assessments_global(
    protocol: str | None = None,
    q: str | None = None,
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=1, le=100),
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Assessment, Patient, ProtocolCatalog)
        .join(Patient, Assessment.patient_id == Patient.id)
        .join(ProtocolCatalog, Assessment.protocol_id == ProtocolCatalog.id)
        .where(Patient.professional_id == professional.id)
    )
    if protocol:
        query = query.where(Assessment.protocol_id == protocol.lower())
    if q:
        query = query.where(Patient.name.ilike(f"%{q}%"))
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    result = await db.execute(query.order_by(Assessment.date.desc()).offset((page - 1) * limit).limit(limit))
    items = [
        _assessment_response(a, proto.name, professional.name, patient=patient)
        for a, patient, proto in result.all()
    ]
    return PaginatedResponse(items=items, total=total or 0, page=page, limit=limit)


patient_router = APIRouter(prefix="/patients/{patient_id}", tags=["clinical"])


@patient_router.get("/assessments", response_model=list[AssessmentResponse])
async def list_patient_assessments(
    patient_id: UUID,
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    await get_patient_for_professional(patient_id, professional, db)
    result = await db.execute(
        select(Assessment, ProtocolCatalog)
        .join(ProtocolCatalog, Assessment.protocol_id == ProtocolCatalog.id)
        .where(Assessment.patient_id == patient_id)
        .order_by(Assessment.date.desc())
    )
    return [
        _assessment_response(a, p.name, professional.name)
        for a, p in result.all()
    ]


@patient_router.post("/assessments", response_model=AssessmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assessment(
    patient_id: UUID,
    body: AssessmentCreate,
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    await get_patient_for_professional(patient_id, professional, db)
    proto = await db.get(ProtocolCatalog, body.protocol_id.lower())
    if not proto:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado")

    answers = body.answers or {}
    scores = body.scores
    result_text = body.result
    percentage = body.percentage
    interpretation = body.interpretation
    fields = [f.model_dump() for f in body.fields]

    if answers and get_protocol_scoring_mode(proto.id) == "manifest" and scores is None:
        try:
            scores = score_manifest_protocol(proto.id, answers)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail="Pacote do instrumento não encontrado") from exc

    if scores:
        derived = build_assessment_from_scores(scores)
        if not result_text:
            result_text = derived["result"]
        if not percentage:
            percentage = derived["percentage"]
        if not interpretation:
            interpretation = derived["interpretation"]
        if not fields:
            fields = derived["fields"]

    if not result_text:
        raise HTTPException(status_code=400, detail="Resultado da avaliação é obrigatório")

    assessment = Assessment(
        patient_id=patient_id,
        professional_id=professional.id,
        protocol_id=proto.id,
        date=date.fromisoformat(body.date) if body.date else date.today(),
        result=result_text,
        percentage=percentage,
        interpretation=interpretation,
        fields=fields,
        answers=answers,
        scores=scores,
        status=body.status,
        informant=body.informant,
        assessment_metadata=body.metadata,
    )
    db.add(assessment)
    await db.flush()
    await create_timeline_event(
        db,
        patient_id=patient_id,
        professional_id=professional.id,
        event_type="avaliacao",
        title=f"Avaliação {proto.name} aplicada",
        description=result_text,
        source_id=assessment.id,
    )
    return _assessment_response(assessment, proto.name, professional.name)


@patient_router.get("/goals", response_model=list[GoalResponse])
async def list_goals(
    patient_id: UUID,
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    await get_patient_for_professional(patient_id, professional, db)
    result = await db.execute(select(Goal).where(Goal.patient_id == patient_id))
    return [
        GoalResponse(
            id=str(g.id),
            title=g.title,
            progress=g.progress,
            area=g.area,
            professional=professional.name,
            start_date=g.start_date.isoformat(),
            status=g.status,
        )
        for g in result.scalars().all()
    ]


@patient_router.post("/goals", response_model=GoalResponse, status_code=status.HTTP_201_CREATED)
async def create_goal(
    patient_id: UUID,
    body: GoalCreate,
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    await get_patient_for_professional(patient_id, professional, db)
    progress = body.progress
    status_val = body.status or goal_status_from_progress(progress)
    goal = Goal(
        patient_id=patient_id,
        professional_id=professional.id,
        title=body.title,
        area=body.area,
        progress=progress,
        start_date=date.fromisoformat(body.start_date) if body.start_date else date.today(),
        status=status_val,
    )
    db.add(goal)
    await db.flush()
    return GoalResponse(
        id=str(goal.id),
        title=goal.title,
        progress=goal.progress,
        area=goal.area,
        professional=professional.name,
        start_date=goal.start_date.isoformat(),
        status=goal.status,
    )


@patient_router.patch("/goals/{goal_id}", response_model=GoalResponse)
async def update_goal(
    patient_id: UUID,
    goal_id: UUID,
    body: GoalUpdate,
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    await get_patient_for_professional(patient_id, professional, db)
    result = await db.execute(select(Goal).where(Goal.id == goal_id, Goal.patient_id == patient_id))
    goal = result.scalar_one_or_none()
    if not goal:
        raise HTTPException(status_code=404, detail="Meta não encontrada")
    data = body.model_dump(exclude_unset=True)
    if "progress" in data and "status" not in data:
        data["status"] = goal_status_from_progress(data["progress"])
    for field, value in data.items():
        setattr(goal, field, value)
    await db.flush()
    if goal.progress >= 75:
        await create_timeline_event(
            db,
            patient_id=patient_id,
            professional_id=professional.id,
            event_type="meta",
            title="Meta atingida",
            description=goal.title,
            source_id=goal.id,
        )
    return GoalResponse(
        id=str(goal.id),
        title=goal.title,
        progress=goal.progress,
        area=goal.area,
        professional=professional.name,
        start_date=goal.start_date.isoformat(),
        status=goal.status,
    )


@patient_router.get("/clinical-domains")
async def get_clinical_domains(
    patient_id: UUID,
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    await get_patient_for_professional(patient_id, professional, db)
    return await build_clinical_domains(db, patient_id)


@router.get("/analytics/development")
async def analytics_development(
    patient_id: UUID | None = Query(None),
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    if patient_id:
        await get_patient_for_professional(patient_id, professional, db)
        domains = await build_clinical_domains(db, patient_id)
        return {"areas": domains}
    return {"areas": []}
