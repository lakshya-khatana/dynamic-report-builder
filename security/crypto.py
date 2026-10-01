"""
Spec §1.3: 'All database passwords ... stored encrypted at rest.'
Symmetric encryption via Fernet — same key encrypts and decrypts, so the key
itself must never be committed to git (it lives only in .env).
"""

from cryptography.fernet import Fernet, InvalidToken

from config import settings


def _get_fernet() -> Fernet:
    if not settings.FERNET_KEY:
        raise RuntimeError(
            "FERNET_KEY is not set. Generate one with: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\" "
            "and put it in .env before storing any credentials."
        )
    return Fernet(settings.FERNET_KEY.encode())


def encrypt(plaintext: str) -> str:
    """Returns a base64 token safe to store in a text column."""
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt(token: str) -> str:
    try:
        return _get_fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        # Wrong key, corrupted value, or tampered data — never leak which.
        raise ValueError("Stored credential could not be decrypted.") from None


def encrypt_config(config: dict, sensitive_keys: tuple[str, ...] = ("password",)) -> dict:
    """Encrypt only the sensitive fields of a source config dict, leave the rest plain."""
    out = dict(config)
    for key in sensitive_keys:
        if key in out and out[key] is not None:
            out[key] = encrypt(out[key])
    return out


def decrypt_config(config: dict, sensitive_keys: tuple[str, ...] = ("password",)) -> dict:
    out = dict(config)
    for key in sensitive_keys:
        if key in out and out[key] is not None:
            out[key] = decrypt(out[key])
    return out
