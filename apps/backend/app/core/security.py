from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from typing import Any
from uuid import uuid4

from jose import jwt
from passlib.context import CryptContext

from app.core.settings import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_token(subject: str, expires_delta: timedelta, token_type: str, token_id: str | None = None) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "jti": token_id or str(uuid4()),
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=ALGORITHM)


def create_access_token(subject: str) -> str:
    settings = get_settings()
    return create_token(
        subject=subject,
        expires_delta=timedelta(minutes=settings.jwt_access_token_minutes),
        token_type="access",
    )


def create_refresh_token(subject: str, token_id: str | None = None) -> str:
    settings = get_settings()
    return create_token(
        subject=subject,
        expires_delta=timedelta(days=settings.jwt_refresh_token_days),
        token_type="refresh",
        token_id=token_id,
    )


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[ALGORITHM])


def hash_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()
