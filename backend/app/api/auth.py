"""
Multi-Device Authentication, JWT Access/Refresh Rotation, and Session Management Routes.
"""

from typing import List, Optional
from datetime import datetime, timedelta, timezone
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.db.session import get_db
from app.core.config import settings
from app.models.user import User, RefreshToken
from app.schemas.user import (
    UserCreate,
    UserLogin,
    UserResponse,
    TokenResponse,
    ConsentUpdate,
    RefreshTokenRequest,
    LogoutRequest,
    DeviceSessionInfo,
)
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token_detailed,
    generate_refresh_token,
    hash_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


async def _issue_device_tokens(
    db: AsyncSession,
    user: User,
    device_id: Optional[str] = None,
    device_name: Optional[str] = None,
    platform: Optional[str] = None,
) -> TokenResponse:
    resolved_device_id = (device_id or "").strip() or f"dev-{uuid.uuid4().hex[:12]}"
    raw_refresh = generate_refresh_token()
    now = datetime.now(timezone.utc)
    refresh_expires = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    # Revoke prior active refresh tokens for this exact device_id (keeps other phones logged in!)
    if device_id:
        await db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user.id,
                RefreshToken.device_id == resolved_device_id,
                RefreshToken.is_revoked.is_(False),
            )
            .values(is_revoked=True, revoked_at=now)
        )

    db_refresh = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_refresh),
        device_id=resolved_device_id,
        device_name=device_name or "Mobile / Web Client",
        platform=platform or "unknown",
        created_at=now,
        last_used_at=now,
        expires_at=refresh_expires,
        is_revoked=False,
    )
    db.add(db_refresh)
    await db.commit()

    access_token = create_access_token(user.id, device_id=resolved_device_id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        token_type="bearer",
        device_id=resolved_device_id,
        user=UserResponse.model_validate(user),
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency to retrieve authenticated user from JWT access token."""
    user_id, _, token_status = decode_access_token_detailed(token)
    if token_status == "EXPIRED":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Access token expired",
            headers={"WWW-Authenticate": "Bearer", "X-Token-Status": "EXPIRED"},
        )
    if not user_id or token_status != "VALID":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account inactive or not found",
        )
    return user


@router.post("/register", response_model=TokenResponse)
async def register(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    """Registers a new user/researcher with explicit consent and multi-device token issuance."""
    if not payload.consent_accepted:
        raise HTTPException(
            status_code=400,
            detail="Explicit research protocol consent must be accepted before registration.",
        )

    normalized_email = payload.email.strip().lower()
    existing = await db.execute(select(User).where(User.email == normalized_email))
    if existing.scalars().first():
        raise HTTPException(status_code=400, detail="An account with this email already exists")

    new_user = User(
        email=normalized_email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name.strip() if payload.full_name else None,
        consent_accepted=payload.consent_accepted,
        role="researcher",
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    return await _issue_device_tokens(
        db=db,
        user=new_user,
        device_id=payload.device_id,
        device_name=payload.device_name,
        platform=payload.platform,
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: UserLogin, db: AsyncSession = Depends(get_db)):
    """Authenticates user across multiple devices with email normalization and device tracking."""
    normalized_email = payload.email.strip().lower()
    result = await db.execute(select(User).where(User.email == normalized_email))
    user = result.scalars().first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="User account is disabled")

    return await _issue_device_tokens(
        db=db,
        user=user,
        device_id=payload.device_id,
        device_name=payload.device_name,
        platform=payload.platform,
    )


@router.post("/token", response_model=TokenResponse)
async def login_oauth_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """OAuth2 standard form-data login endpoint for Swagger UI and API clients."""
    normalized_email = form_data.username.strip().lower()
    result = await db.execute(select(User).where(User.email == normalized_email))
    user = result.scalars().first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    return await _issue_device_tokens(db=db, user=user, platform="oauth2_form")


@router.post("/refresh", response_model=TokenResponse)
async def refresh_session(payload: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    """
    Rotates a valid refresh token and returns a fresh access + refresh token pair.
    Implements replay protection: presenting a previously revoked token invalidates
    all tokens for that user/device.
    """
    token_hash = hash_refresh_token(payload.refresh_token)
    res = await db.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
    rt = res.scalars().first()

    if not rt:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    now = datetime.now(timezone.utc)
    if rt.is_revoked:
        # Replay protection: revoke all tokens on that device
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == rt.user_id, RefreshToken.device_id == rt.device_id)
            .values(is_revoked=True, revoked_at=now)
        )
        await db.commit()
        raise HTTPException(status_code=401, detail="Refresh token has been revoked. Please sign in again.")

    expires_at = _as_utc(rt.expires_at)
    if expires_at and expires_at < now:
        rt.is_revoked = True
        rt.revoked_at = now
        await db.commit()
        raise HTTPException(status_code=401, detail="Refresh token expired. Please sign in again.")

    if payload.device_id and payload.device_id != rt.device_id:
        raise HTTPException(status_code=401, detail="Refresh token device mismatch")

    user_res = await db.execute(select(User).where(User.id == rt.user_id))
    user = user_res.scalars().first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User account inactive or not found")

    # Rotate: revoke used token and issue fresh pair
    rt.is_revoked = True
    rt.revoked_at = now

    new_raw_refresh = generate_refresh_token()
    new_rt = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(new_raw_refresh),
        device_id=rt.device_id,
        device_name=rt.device_name,
        platform=rt.platform,
        created_at=now,
        last_used_at=now,
        expires_at=now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        is_revoked=False,
    )
    db.add(new_rt)
    await db.commit()

    access_token = create_access_token(user.id, device_id=rt.device_id)
    return TokenResponse(
        access_token=access_token,
        refresh_token=new_raw_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        token_type="bearer",
        device_id=rt.device_id,
        user=UserResponse.model_validate(user),
    )


@router.post("/logout")
async def logout(
    payload: LogoutRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Logs out current device by revoking its refresh token or device_id."""
    now = datetime.now(timezone.utc)
    revoked_count = 0

    if payload.refresh_token:
        t_hash = hash_refresh_token(payload.refresh_token)
        res = await db.execute(
            select(RefreshToken).where(
                RefreshToken.token_hash == t_hash,
                RefreshToken.user_id == current_user.id,
                RefreshToken.is_revoked.is_(False),
            )
        )
        rt = res.scalars().first()
        if rt:
            rt.is_revoked = True
            rt.revoked_at = now
            revoked_count += 1
    elif payload.device_id:
        res = await db.execute(
            select(RefreshToken).where(
                RefreshToken.device_id == payload.device_id,
                RefreshToken.user_id == current_user.id,
                RefreshToken.is_revoked.is_(False),
            )
        )
        for rt in res.scalars().all():
            rt.is_revoked = True
            rt.revoked_at = now
            revoked_count += 1

    await db.commit()
    return {"status": "LOGGED_OUT", "revoked_sessions": revoked_count}


@router.post("/logout-all")
async def logout_all_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revokes all active refresh tokens across every device for the authenticated user."""
    now = datetime.now(timezone.utc)
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == current_user.id, RefreshToken.is_revoked.is_(False))
        .values(is_revoked=True, revoked_at=now)
    )
    await db.commit()
    return {"status": "ALL_DEVICES_LOGGED_OUT"}


@router.get("/devices", response_model=List[DeviceSessionInfo])
async def list_device_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lists active and recent device authentication sessions for the user."""
    res = await db.execute(
        select(RefreshToken)
        .where(RefreshToken.user_id == current_user.id)
        .order_by(RefreshToken.last_used_at.desc())
    )
    return [DeviceSessionInfo.model_validate(rt) for rt in res.scalars().all()]


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Returns profile and consent status of current authenticated user."""
    return UserResponse.model_validate(current_user)


@router.post("/consent", response_model=UserResponse)
async def update_consent(
    payload: ConsentUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Updates biometric data consent."""
    current_user.consent_accepted = payload.consent_accepted
    await db.commit()
    await db.refresh(current_user)
    return UserResponse.model_validate(current_user)
