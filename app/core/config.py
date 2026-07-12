from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Korus One API"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    cors_origins: str = (
        "http://localhost:3000,"
        "http://localhost:5173,"
        "http://localhost:4173,"
        "http://127.0.0.1:3000,"
        "http://127.0.0.1:5173,"
        "http://127.0.0.1:4173"
    )

    database_url: str = "postgresql+asyncpg://korus:korus@localhost:5433/korus_one"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    redis_url: str = "redis://localhost:6380"

    resend_api_key: str = ""
    email_from: str = "Korus One <noreply@korusone.com.br>"
    email_sending_enabled: bool = False
    password_token_expire_minutes: int = 60
    password_reset_cooldown_seconds: int = 60

    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "korus-attachments"
    s3_region: str = "us-east-1"

    opencode_api_key: str = ""
    opencode_base_url: str = "https://opencode.ai/zen/v1"
    opencode_model: str = "deepseek-v4-flash"

    # Assistente de IA unificado (clínico + gestão) com tool-calling.
    assistant_rate_limit_per_hour: int = 30
    assistant_llm_timeout_seconds: int = 120
    ai_context_max_chars: int = 12000

    whatsapp_provider: str = "evolution"
    whatsapp_credential_encryption_key: str = ""
    app_public_url: str = ""
    evolution_api_base_url: str = "http://localhost:8080"
    evolution_global_api_key: str = ""
    evolution_webhook_secret: str = ""
    clinic_timezone: str = "America/Sao_Paulo"
    whatsapp_scheduler_interval_seconds: int = 900
    whatsapp_reminder_window_hours: int = 24
    whatsapp_reminder_tolerance_minutes: int = 15
    whatsapp_billing_reminder_days_before: int = 3

    billing_provider: str = "stub"
    asaas_api_key: str = ""
    asaas_api_base_url: str = "https://sandbox.asaas.com/api/v3"
    asaas_webhook_token: str = ""
    frontend_url: str = "http://localhost:5173"
    trial_days: int = 7

    instrument_packages_root: str = ""
    spm_content_package_path: str = ""
    spm_informant_link_expire_days: int = 14

    max_upload_bytes: int = 26214400

    @field_validator("evolution_api_base_url", mode="before")
    @classmethod
    def normalize_evolution_api_base_url(cls, value: object) -> str:
        url = str(value or "").strip().rstrip("/")
        if not url:
            return url
        if url.startswith(("http://", "https://")):
            return url
        if url.startswith(("localhost", "127.0.0.1")):
            return f"http://{url}"
        return f"https://{url}"

    @property
    def effective_billing_provider(self) -> str:
        provider = self.billing_provider.lower().strip() or "stub"
        asaas_key = self.asaas_api_key.strip()
        if provider == "asaas":
            if not asaas_key:
                return "stub"
            # Chaves reais Asaas começam com $aact_; placeholders em dev usam stub.
            if self.debug and not asaas_key.startswith("$aact_"):
                return "stub"
            return "asaas"
        return provider

    @property
    def billing_frontend_base_url(self) -> str:
        return (self.frontend_url or "").rstrip("/") or self.cors_origin_list[0]

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def public_api_base_url(self) -> str | None:
        base = (self.app_public_url or "").strip()
        return base or None

    @property
    def evolution_webhook_url(self) -> str | None:
        base = self.public_api_base_url
        if not base:
            return None
        return f"{base.rstrip('/')}/api/v1/webhooks/evolution/whatsapp"


INSECURE_JWT_SECRETS = frozenset({"change-me-in-production", ""})


def validate_settings(settings: Settings) -> None:
    if settings.debug:
        return
    secret = (settings.jwt_secret or "").strip()
    if secret in INSECURE_JWT_SECRETS or len(secret) < 32:
        raise RuntimeError(
            "JWT_SECRET inseguro ou ausente: defina um segredo forte com debug=False"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
