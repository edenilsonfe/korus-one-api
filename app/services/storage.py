import uuid
from contextlib import asynccontextmanager

import aioboto3
from botocore.config import Config

from app.core.config import get_settings


class StorageService:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._session = aioboto3.Session()

    @asynccontextmanager
    async def _client(self):
        async with self._session.client(
            "s3",
            endpoint_url=self.settings.s3_endpoint,
            aws_access_key_id=self.settings.s3_access_key,
            aws_secret_access_key=self.settings.s3_secret_key,
            region_name=self.settings.s3_region,
            config=Config(signature_version="s3v4"),
        ) as client:
            yield client

    async def ensure_bucket(self) -> None:
        async with self._client() as client:
            try:
                await client.head_bucket(Bucket=self.settings.s3_bucket)
            except Exception:
                await client.create_bucket(Bucket=self.settings.s3_bucket)

    async def upload(self, key: str, body: bytes, content_type: str) -> str:
        await self.ensure_bucket()
        async with self._client() as client:
            await client.put_object(
                Bucket=self.settings.s3_bucket,
                Key=key,
                Body=body,
                ContentType=content_type,
            )
        return key

    async def presigned_url(self, key: str, expires: int = 3600) -> str:
        async with self._client() as client:
            return await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.settings.s3_bucket, "Key": key},
                ExpiresIn=expires,
            )

    @staticmethod
    def make_key(patient_id: uuid.UUID, filename: str) -> str:
        return f"patients/{patient_id}/{uuid.uuid4()}/{filename}"


storage_service = StorageService()
