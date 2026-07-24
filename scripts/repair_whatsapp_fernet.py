"""Re-encrypt Evolution instance credentials after Fernet key rotation.

Run with production env:
  railway run --project <id> --environment production --service api -- python scripts/repair_whatsapp_fernet.py
"""

from __future__ import annotations

import asyncio
import sys

from sqlalchemy import select

from app.core.config import get_settings
from app.db.session import AsyncSessionLocal
from app.models.whatsapp_connection import WhatsAppConnection
from app.services.evolution_api_client import EvolutionApiClient
from app.utils.credential_encryption import (
    CredentialEncryptionError,
    decrypt_secret,
    encrypt_secret,
    _get_fernet,
)


async def main() -> int:
    _get_fernet.cache_clear()
    settings = get_settings()
    if not settings.evolution_global_api_key:
        print("EVOLUTION_GLOBAL_API_KEY missing", file=sys.stderr)
        return 1
    if not settings.whatsapp_credential_encryption_key:
        print("WHATSAPP_CREDENTIAL_ENCRYPTION_KEY missing", file=sys.stderr)
        return 1

    client = EvolutionApiClient()
    repaired = 0
    ok = 0

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(WhatsAppConnection).where(WhatsAppConnection.provider == "evolution")
        )
        rows = list(result.scalars().all())
        print(f"connections={len(rows)}")

        for connection in rows:
            token = (
                connection.encrypted_instance_api_key
                or connection.encrypted_access_token
            )
            print(
                f"id={connection.id} status={connection.status} "
                f"instance={connection.evolution_instance_name} has_token={bool(token)}"
            )
            if not token:
                continue
            try:
                decrypt_secret(token)
                print("  decrypt=ok")
                ok += 1
                continue
            except CredentialEncryptionError as exc:
                print(f"  decrypt=fail ({exc})")

            plaintext = None
            instance_name = connection.evolution_instance_name
            if instance_name:
                try:
                    listing = await client.fetch_instances(
                        instance_name, api_key=settings.evolution_global_api_key
                    )
                except Exception as exc:  # noqa: BLE001 - repair script
                    print(f"  fetch_instances_error={type(exc).__name__}:{exc}")
                    listing = None
                if isinstance(listing, list):
                    for item in listing:
                        if not isinstance(item, dict):
                            continue
                        extracted = EvolutionApiClient.extract_instance_api_key(item)
                        if extracted:
                            plaintext = extracted
                            break

            if not plaintext:
                # Evolution accepts the global admin key for send/instance ops.
                plaintext = settings.evolution_global_api_key
                print("  using_global_key_as_instance_credential")

            connection.encrypted_instance_api_key = encrypt_secret(plaintext)
            repaired += 1
            print("  reencrypted=ok")

        await db.commit()

    print(f"done ok={ok} repaired={repaired}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
