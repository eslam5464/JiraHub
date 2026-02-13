import secrets

from cryptography.fernet import Fernet, InvalidToken
from pwdlib import PasswordHash

from app.core.config import get_settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a password using Argon2id."""
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its Argon2id hash."""
    return password_hash.verify(plain_password, hashed_password)


def encrypt_token(token: str) -> str:
    """Encrypt a Jira API token using Fernet symmetric encryption."""
    settings = get_settings()
    f = Fernet(settings.encryption_key.encode())
    return f.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a Jira API token."""
    settings = get_settings()
    f = Fernet(settings.encryption_key.encode())
    try:
        return f.decrypt(encrypted_token.encode()).decode()
    except InvalidToken as e:
        raise ValueError("Failed to decrypt token - encryption key may have changed") from e


def generate_session_token() -> str:
    """Generate a cryptographically secure session token."""
    return secrets.token_urlsafe(32)
