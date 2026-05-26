from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from jose import JWTError
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.core.settings import get_settings
from app.db.session import get_db
from app.models import RefreshToken, User, UserProfile
from app.modules.auth.bootstrap import bootstrap_user_defaults

router = APIRouter()


class AuthRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class CallsignRequest(BaseModel):
    callsign: str = Field(min_length=3, max_length=20)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    callsign: str | None
    requires_callsign: bool


def normalize_email(email: str) -> str:
    return email.lower().strip()


def normalize_callsign(callsign: str) -> str:
    value = callsign.strip().upper()
    if not re.fullmatch(r"[A-Z0-9_-]{3,20}", value):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Callsign must be 3-20 characters using letters, numbers, underscores, or hyphens.",
        )
    return value


async def issue_token_pair(db: AsyncSession, user: User) -> TokenPair:
    settings = get_settings()
    access_token = create_access_token(user.id)
    refresh_token = create_refresh_token(user.id)
    token_record = RefreshToken(
        user_id=user.id,
        token_hash=hash_token(refresh_token),
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_days),
    )
    db.add(token_record)
    await db.commit()
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


async def build_user_response(db: AsyncSession, user: User) -> UserResponse:
    profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    callsign = profile.callsign if profile else None
    return UserResponse(
        id=user.id,
        email=user.email,
        callsign=callsign,
        requires_callsign=callsign is None,
    )


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
async def register(payload: AuthRequest, db: Annotated[AsyncSession, Depends(get_db)]) -> TokenPair:
    email = normalize_email(payload.email)
    existing = await db.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(email=email, password_hash=hash_password(payload.password))
    db.add(user)
    await db.flush()
    db.add_all(bootstrap_user_defaults(user))
    await db.commit()
    await db.refresh(user)
    return await issue_token_pair(db, user)


@router.post("/login", response_model=TokenPair)
async def login(payload: AuthRequest, db: Annotated[AsyncSession, Depends(get_db)]) -> TokenPair:
    email = normalize_email(payload.email)
    user = await db.scalar(select(User).where(User.email == email, User.is_active.is_(True)))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    return await issue_token_pair(db, user)


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshRequest, db: Annotated[AsyncSession, Depends(get_db)]) -> TokenPair:
    try:
        token_payload = decode_token(payload.refresh_token)
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token") from exc

    if token_payload.get("type") != "refresh" or not token_payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    token_hash = hash_token(payload.refresh_token)
    token_record = await db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    if token_record is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token revoked or expired")

    user = await db.scalar(select(User).where(User.id == token_payload["sub"], User.is_active.is_(True)))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    token_record.revoked_at = datetime.now(timezone.utc)
    db.add(token_record)
    return await issue_token_pair(db, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, response_class=Response, response_model=None)
async def logout(payload: RefreshRequest, db: Annotated[AsyncSession, Depends(get_db)]) -> None:
    token_record = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == hash_token(payload.refresh_token)))
    if token_record is not None:
        token_record.revoked_at = datetime.now(timezone.utc)
        db.add(token_record)
        await db.commit()


@router.get("/me", response_model=UserResponse)
async def me(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    return await build_user_response(db, user)


@router.post("/callsign", response_model=UserResponse)
async def set_callsign(
    payload: CallsignRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserResponse:
    callsign = normalize_callsign(payload.callsign)
    existing = await db.scalar(select(UserProfile).where(UserProfile.callsign == callsign, UserProfile.user_id != user.id))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Callsign already taken")

    profile = await db.scalar(select(UserProfile).where(UserProfile.user_id == user.id))
    if profile is None:
        profile = UserProfile(user_id=user.id)

    profile.callsign = callsign
    db.add(profile)
    await db.commit()
    return await build_user_response(db, user)
