"""Sentry bootstrap for the FastAPI app and ARQ worker."""

from __future__ import annotations

import os

import sentry_sdk
from sentry_sdk.integrations.arq import ArqIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from app.core.config import Settings
from app.services.sentry_scrubbing import scrub_sentry_event


def init_sentry(settings: Settings) -> bool:
    dsn = (settings.sentry_dsn or "").strip()
    if not dsn:
        return False

    environment = (settings.sentry_environment or "").strip() or (
        "development" if settings.debug else "production"
    )
    traces = settings.sentry_traces_sample_rate
    if traces is None:
        traces = 0.0 if settings.debug else 0.1

    release = (settings.sentry_release or os.getenv("SENTRY_RELEASE") or "").strip() or None

    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        release=release,
        send_default_pii=False,
        traces_sample_rate=traces,
        before_send=scrub_sentry_event,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
            SqlalchemyIntegration(),
            ArqIntegration(),
        ],
    )
    return True
