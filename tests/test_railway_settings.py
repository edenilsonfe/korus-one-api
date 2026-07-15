"""Helpers de deploy Railway / AWS S3."""

from app.core.config import Settings
from app.services.storage import s3_client_kwargs


def test_database_url_normalizes_postgres_scheme_to_asyncpg():
    s = Settings(
        database_url="postgresql://korus:korus@localhost:5432/korus_one",
        jwt_secret="x" * 32,
        debug=True,
    )
    assert s.database_url.startswith("postgresql+asyncpg://")
    assert "korus:korus@localhost:5432/korus_one" in s.database_url


def test_database_url_keeps_asyncpg_scheme():
    s = Settings(
        database_url="postgresql+asyncpg://korus:korus@localhost:5432/korus_one",
        jwt_secret="x" * 32,
        debug=True,
    )
    assert s.database_url == "postgresql+asyncpg://korus:korus@localhost:5432/korus_one"


def test_s3_client_kwargs_omits_endpoint_when_empty():
    s = Settings(
        s3_endpoint="",
        s3_access_key="AKIA",
        s3_secret_key="secret",
        s3_bucket="bucket",
        s3_region="us-east-1",
        jwt_secret="x" * 32,
        debug=True,
    )
    kwargs = s3_client_kwargs(s)
    assert "endpoint_url" not in kwargs
    assert kwargs["aws_access_key_id"] == "AKIA"
    assert kwargs["region_name"] == "us-east-1"


def test_s3_client_kwargs_keeps_minio_endpoint():
    s = Settings(
        s3_endpoint="http://localhost:9000",
        s3_access_key="minioadmin",
        s3_secret_key="minioadmin",
        s3_bucket="bucket",
        s3_region="us-east-1",
        jwt_secret="x" * 32,
        debug=True,
    )
    kwargs = s3_client_kwargs(s)
    assert kwargs["endpoint_url"] == "http://localhost:9000"
