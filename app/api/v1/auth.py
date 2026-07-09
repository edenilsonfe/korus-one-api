from datetime import UTC, datetime, timedelta

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.core.specialty_catalog import specialty_label
from app.models.professional import Professional
from app.schemas.auth import LoginRequest, RefreshRequest, RegisterRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


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
        cpf=body.cpf,
        subscription_status="trialing",
        trial_started_at=now,
        trial_ends_at=now + timedelta(days=trial_days),
    )
    db.add(professional)
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
