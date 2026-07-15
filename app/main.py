from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import get_settings, validate_settings
from app.db.session import AsyncSessionLocal
from app.middleware.entitlement import EntitlementMiddleware
from app.seeds.demo import seed_protocols
from app.services.plan_catalog_seed import seed_plan_catalog
from app.services.sentry_init import init_sentry

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncSessionLocal() as session:
        # Catálogo de protocolos (idempotente) — sem isto /protocolos fica vazio em prod.
        await seed_protocols(session)
        await seed_plan_catalog(session)
        await session.commit()
    logger.info("Protocol and plan catalog seed checked")
    try:
        yield
    finally:
        from app.services.evolution_api_client import EvolutionApiClient

        await EvolutionApiClient.aclose_shared()



def create_app() -> FastAPI:
    settings = get_settings()
    validate_settings(settings)
    if init_sentry(settings):
        logger.info("Sentry initialized")
    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    cors_kwargs: dict = {
        "allow_credentials": True,
        "allow_methods": ["*"],
        "allow_headers": ["*"],
        "expose_headers": ["Content-Type"],
    }
    if settings.debug:
        # Dev: aceita qualquer porta em localhost / 127.0.0.1
        cors_kwargs["allow_origin_regex"] = r"https?://(localhost|127\.0\.0\.1)(:\d+)?"
    else:
        cors_kwargs["allow_origins"] = settings.cors_origin_list

    app.add_middleware(CORSMiddleware, **cors_kwargs)
    app.add_middleware(EntitlementMiddleware)
    app.include_router(api_router, prefix=settings.api_v1_prefix)

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    return app


app = create_app()
