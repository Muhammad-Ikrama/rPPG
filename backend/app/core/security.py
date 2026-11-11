"""
Security, Password Hashing, and Multi-Device JWT / Refresh Token Utilities.
Uses direct bcrypt implementation to eliminate passlib version incompatibilities.
"""

from typing import Optional, Any, Union, Dict, Tuple
from datetime import datetime, timedelta, timezone
import hashlib
import secrets
import uuid
from jose import jwt, ExpiredSignatureError, JWTError
import bcrypt
from app.core.config import settings


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored bcrypt hash."""
    try:
        pwd_bytes = plain_password[:72].encode("utf-8")
        hash_bytes = hashed_password.encode("utf-8")
        return bcrypt.checkpw(pwd_bytes, hash_bytes)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    """Generates bcrypt hash of password."""
    pwd_bytes = password[:72].encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


def create_access_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None,
    device_id: Optional[str] = None,
) -> str:
    """Creates a signed short-lived JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode: Dict[str, Any] = {
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "sub": str(subject),
        "type": "access",
    }
    if device_id:
        to_encode["device_id"] = device_id

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token_detailed(token: str) -> Tuple[Optional[str], Optional[Dict[str, Any]], str]:
    """
    Decodes and validates a JWT access token.

    Returns:
        (user_id, payload, status) where status is one of:
        'VALID', 'EXPIRED', 'INVALID'.
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        if payload.get("type") not in (None, "access"):
            return None, None, "INVALID"
        user_id: Optional[str] = payload.get("sub")
        if not user_id:
            return None, None, "INVALID"
        return user_id, payload, "VALID"
    except ExpiredSignatureError:
        return None, None, "EXPIRED"
    except JWTError:
        return None, None, "INVALID"
    except Exception:
        return None, None, "INVALID"


def decode_access_token(token: str) -> Optional[str]:
    """Decodes and validates JWT token, returning the subject (user_id) or None."""
    user_id, _, status = decode_access_token_detailed(token)
    return user_id if status == "VALID" else None


def generate_refresh_token() -> str:
    """Generates a cryptographically random opaque refresh token for multi-device sessions."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(raw_token: str) -> str:
    """Returns SHA-256 hex digest of a raw refresh token for safe database persistence."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
