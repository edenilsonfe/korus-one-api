from datetime import UTC, date, datetime, timedelta

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.demo_patient import (
    DEMO_AVATAR_COLOR,
    DEMO_PATIENT_NAME,
    demo_patient_birth_date,
)
from app.core.deps import get_current_professional
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.core.specialty_catalog import specialty_label
from app.models.patient import Patient
from app.models.professional import Professional
from app.schemas.auth import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from app.services.auth_rate_limit import enforce_forgot_rate_limit, enforce_reset_rate_limit
from app.services.password_reset import (
    GENERIC_FORGOT_MESSAGE,
    change_password,
    request_password_reset,
    reset_password_with_token,
    send_password_reset_email_sync,
)

router = APIRouter(prefix="/auth", tags=["auth"])


def _request_ip(request: Request) -> str:
    x_forwarded_for = request.headers.get("x-forwarded-for", "")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def send_password_reset_email_task(to_email: str, user_name: str, raw_token: str) -> None:
    send_password_reset_email_sync(to_email=to_email, user_name=user_name, raw_token=raw_token)


def _tokens_for(professional: Professional) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(professional.id, professional.token_version),
        refresh_token=create_refresh_token(professional.id, professional.token_version),
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(Professional).where(Professional.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="E-mail já cadastrado")
    settings = get_settings()
    now = datetime.now(UTC)
    trial_days = settings.trial_days
    professional = Professional(
        email=body.email,
        password_hash=hash_password(body.password),
        name=body.name,
        specialty_key=body.specialty_key,
        specialty=specialty_label(body.specialty_key),
        council=body.council,
        phone=body.phone,
        cpf=body.cpf or "",
        subscription_status="trialing",
        trial_started_at=now,
        trial_ends_at=now + timedelta(days=trial_days),
    )
    db.add(professional)
    await db.flush()
    db.add(
        Patient(
            professional_id=professional.id,
            name=DEMO_PATIENT_NAME,
            birth_date=demo_patient_birth_date(),
            diagnosis_keys=[],
            status="avaliacao",
            start_date=date.today(),
            avatar_color=DEMO_AVATAR_COLOR,
        )
    )
    await db.flush()
    return _tokens_for(professional)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Professional).where(Professional.email == body.email))
    professional = result.scalar_one_or_none()
    if not professional or not verify_password(body.password, professional.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais inválidas")
    if professional.is_disabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Conta desativada")
    return _tokens_for(professional)


@router.post("/refresh", response_model=TokenResponse)
async def refresh(body: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        payload = decode_token(body.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
        professional_id = UUID(payload["sub"])
        token_version = int(payload.get("tv", 0))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido") from exc
    result = await db.execute(select(Professional).where(Professional.id == professional_id))
    professional = result.scalar_one_or_none()
    if not professional:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Profissional não encontrado")
    if professional.is_disabled:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Conta desativada")
    if token_version != professional.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sessão invalidada")
    return _tokens_for(professional)


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    body: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    enforce_forgot_rate_limit(_request_ip(request), body.email)
    result = await request_password_reset(db, body.email)
    if result is not None:
        professional, raw_token = result
        background_tasks.add_task(
            send_password_reset_email_task,
            professional.email,
            professional.name,
            raw_token,
        )
    return MessageResponse(message=GENERIC_FORGOT_MESSAGE)


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    body: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    enforce_reset_rate_limit(_request_ip(request))
    await reset_password_with_token(db=db, raw_token=body.token, new_password=body.new_password)
    return MessageResponse(message="Senha redefinida com sucesso")


@router.post("/change-password", response_model=MessageResponse)
async def change_current_password(
    body: ChangePasswordRequest,
    professional: Professional = Depends(get_current_professional),
    db: AsyncSession = Depends(get_db),
):
    await change_password(
        db=db,
        professional=professional,
        current_password=body.current_password,
        new_password=body.new_password,
    )
    return MessageResponse(message="Senha alterada com sucesso")
