"""Symmetric encryption for WhatsApp provider credentials (Fernet)."""

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


class CredentialEncryptionError(RuntimeError):
    """Raised when credentials cannot be encrypted or decrypted."""


def _normalize_fernet_key(raw: str) -> str:
    key = (raw or "").strip()
    if len(key) >= 2 and key[0] == key[-1] and key[0] in "\"'":
        key = key[1:-1].strip()
    return key


def _fernet_from_key(raw_key: str, *, setting_name: str) -> Fernet:
    key = _normalize_fernet_key(raw_key or "")
    if not key:
        raise CredentialEncryptionError(
            f"{setting_name} is not configured. Generate one with: "
            'python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )
    try:
        return Fernet(key.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise CredentialEncryptionError(f"{setting_name} is not a valid Fernet key.") from exc


@lru_cache(maxsize=1)
def _get_fernet() -> Fernet:
    settings = get_settings()
    return _fernet_from_key(
        settings.whatsapp_credential_encryption_key or "",
        setting_name="WHATSAPP_CREDENTIAL_ENCRYPTION_KEY",
    )


def encrypt_secret(plaintext: str) -> str:
    if plaintext is None:
        raise CredentialEncryptionError("Cannot encrypt a None value.")
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str:
    if not token:
        raise CredentialEncryptionError("Cannot decrypt an empty token.")
    try:
        return _get_fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise CredentialEncryptionError(
            "Stored credential could not be decrypted with the current key."
        ) from exc
