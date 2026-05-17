from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

from app.core.config import settings
from app.core.enums import TokenType, UserRole

_password_hasher = PasswordHasher()


def now_utc() -> datetime:
    return datetime.now(UTC)


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return _password_hasher.verify(hashed_password, password)
    except (VerifyMismatchError, VerificationError):
        return False


def password_needs_rehash(hashed_password: str) -> bool:
    return _password_hasher.check_needs_rehash(hashed_password)


def sha256_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def generate_opaque_token_urlsafe(length: int = 48) -> str:
    return secrets.token_urlsafe(length)


def generate_numeric_otp(length: int | None = None) -> str:
    otp_length = length or settings.PASSWORD_RESET_OTP_LENGTH
    start = 10 ** (otp_length - 1)
    end = (10**otp_length) - 1
    return str(secrets.randbelow(end - start + 1) + start)


def create_jwt_token(
    *,
    subject: str,
    token_type: TokenType,
    role: UserRole | str | None = None,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, str, datetime]:
    issued_at = now_utc()
    expires_at = issued_at + expires_delta
    jti = str(uuid.uuid4())

    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type.value,
        "iat": int(issued_at.timestamp()),
        "exp": int(expires_at.timestamp()),
        "jti": jti,
    }
    if role:
        payload["role"] = str(role)
    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token, jti, expires_at


def decode_jwt_token(token: str, expected_type: TokenType | None = None) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError as exc:
        raise ValueError("Token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise ValueError("Invalid token") from exc

    token_type = payload.get("type")
    if expected_type and token_type != expected_type.value:
        raise ValueError("Invalid token type")
    return payload
