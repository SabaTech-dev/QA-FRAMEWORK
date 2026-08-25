"""
Authentication Service

Provides JWT token generation and validation, password hashing, and user authentication.

Refresh tokens rotate on every use (OWASP API2): each carries a unique
``jti`` plus a ``fam`` (family) identifier, consumed tokens are denied in
Redis until their own expiry, and replaying a consumed token revokes the
whole family with a security alarm.
"""

import time
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

from database import get_db_session
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from models import User
from passlib.context import CryptContext
from schemas import LoginRequest, TokenResponse, UserCreate, UserResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from core.logging_config import get_logger, set_request_id
from src.infrastructure.qa_visual.models import QAVisualPrincipal
from src.infrastructure.refresh_tokens.store import (
    RefreshTokenStore,
    TokenStoreUnavailableError,
)

# Initialize logger
logger = get_logger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Refresh token rotation constants (card 3ae2e5c1, F-2 / OWASP API2)
REFRESH_TOKEN_LIFETIME = timedelta(days=7)
# A family tombstone only needs to outlive the longest-lived member of the
# family, which is bounded by the refresh token lifetime itself.
FAMILY_REVOCATION_TTL_SECONDS = int(REFRESH_TOKEN_LIFETIME.total_seconds())

_refresh_token_store: RefreshTokenStore | None = None


def _redis_url_from_settings() -> str:
    """Build the Redis URL from environment-driven settings only.

    Credentials are never hardcoded: REDIS_PASSWORD comes exclusively from
    the environment (unset for local/CI deployments on 127.0.0.1).
    """
    password_part = f":{settings.redis_password}@" if settings.redis_password else ""
    return f"redis://{password_part}{settings.redis_host}:{settings.redis_port}/0"


def get_refresh_token_store() -> RefreshTokenStore:
    """Lazily create the shared refresh token store (Redis denylist)."""
    global _refresh_token_store
    if _refresh_token_store is None:
        _refresh_token_store = RefreshTokenStore(url=_redis_url_from_settings())
    return _refresh_token_store


# L-1: only these values of the ``type`` claim may authenticate access
# endpoints. ``None`` keeps tokens minted before the type tag valid;
# anything else (``refresh``, unknown types) must use its own flow.
ACCESS_TOKEN_TYPES = (None, "access")

# Security scheme
security = HTTPBearer()


def hash_password(password: str) -> str:
    """Hash a password"""
    logger.debug("Hashing password")
    hashed = pwd_context.hash(password)
    logger.debug("Password hashed successfully")
    return hashed


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[User]:
    """Authenticate a user"""
    logger.info("Authenticating user", username=username)

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if not user:
        logger.warning("Authentication failed - user not found", username=username)
        return None

    if not verify_password(password, user.hashed_password):
        logger.warning(
            "Authentication failed - invalid password",
            username=username,
            user_id=user.id,
        )
        return None

    logger.info("User authenticated successfully", username=username, user_id=user.id)
    return user


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db_session),
) -> User:
    """Get current authenticated user from JWT token"""
    logger.debug("Validating JWT token")

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        username: str = payload.get("sub")
        if username is None:
            logger.warning("JWT validation failed - no subject claim")
            raise credentials_exception
        # L-1: a refresh token (or any non-access type) must never
        # authenticate an access-token endpoint.
        if payload.get("type") not in ACCESS_TOKEN_TYPES:
            logger.warning(
                "JWT validation failed - invalid token type",
                token_type=payload.get("type"),
            )
            raise credentials_exception
    except JWTError as e:
        logger.warning("JWT validation failed", error=str(e))
        raise credentials_exception

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning("JWT validation failed - user not found", username=username)
        raise credentials_exception

    # L-2: deactivated users lose API access immediately, mirroring the
    # refresh and optional paths.
    if not user.is_active:
        logger.warning("JWT validation failed - user inactive", username=username, user_id=user.id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.debug("JWT token validated successfully", username=username, user_id=user.id)
    return user


async def login_for_access_token(auth_request: LoginRequest, db: AsyncSession) -> TokenResponse:
    """Login and return access token"""
    logger.info("Login attempt", username=auth_request.username)

    user = await authenticate_user(db, auth_request.username, auth_request.password)
    if not user:
        logger.warning("Login failed - invalid credentials", username=auth_request.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user.username})
    refresh_token = create_refresh_token(data={"sub": user.username})
    logger.info("Login successful - tokens generated", username=user.username, user_id=user.id)

    return TokenResponse(
        access_token=access_token, token_type="bearer", refresh_token=refresh_token
    )


def create_refresh_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
    family_id: str | None = None,
) -> str:
    """Create a rotating refresh token with a unique ``jti`` per emission.

    Every token also carries a ``fam`` (family) identifier: fresh at login,
    inherited across rotations so a detected reuse can revoke the whole
    family (OWASP API2).
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + REFRESH_TOKEN_LIFETIME

    to_encode.update(
        {
            "exp": expire,
            "type": "refresh",
            "jti": str(uuid4()),
            "fam": family_id or str(uuid4()),
        }
    )
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    logger.debug("Refresh token created", expiry=expire.isoformat())
    return encoded_jwt


async def refresh_access_token(
    refresh_token: str,
    db: AsyncSession,
    store: RefreshTokenStore | None = None,
) -> TokenResponse:
    """Rotate a refresh token: issue a new pair and deny the consumed one.

    OWASP API2 hardening (card 3ae2e5c1, F-2):

    - every successful refresh mints a NEW access + refresh token pair and
      denylists the consumed ``jti`` in Redis (TTL = remaining lifetime);
    - replaying a consumed token answers 401, revokes its whole family and
      raises a security alarm log;
    - tokens from an already-revoked family are rejected outright;
    - if the Redis store is unavailable the refresh fails CLOSED (503):
      a denylist that cannot be checked must not be bypassed.
    """
    logger.info("Refreshing access token")
    token_store = store if store is not None else get_refresh_token_store()

    try:
        payload = jwt.decode(
            refresh_token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )

        # Verify it's a refresh token
        token_type = payload.get("type")
        if token_type != "refresh":
            logger.warning("Invalid token type for refresh", token_type=token_type)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify user exists and is active
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            logger.warning("Refresh token - user not found or inactive", username=username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive",
                headers={"WWW-Authenticate": "Bearer"},
            )

        jti = payload.get("jti")
        family_id = payload.get("fam")

        # Family already revoked: any presentation is a replay attempt.
        if family_id and await token_store.is_family_revoked(family_id):
            logger.error(
                "SECURITY: refresh token presented for revoked family "
                "(possible replay or stolen token)",
                username=username,
                jti=jti,
                fam=family_id,
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Reuse detection: atomically consume the jti. If it was already
        # consumed (SET-NX lost the race or an outright replay), revoke
        # the whole family and raise the security alarm.
        if jti is not None:
            exp = payload.get("exp")
            remaining_seconds = max(1, int(exp - time.time())) if exp else 1
            consumed = await token_store.try_consume_jti(jti, ttl_seconds=remaining_seconds)
            if not consumed:
                if family_id:
                    await token_store.revoke_family(
                        family_id, ttl_seconds=FAMILY_REVOCATION_TTL_SECONDS
                    )
                logger.error(
                    "SECURITY: refresh token reuse detected - token family revoked",
                    username=username,
                    jti=jti,
                    fam=family_id,
                )
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid refresh token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        if jti is None:
            # Tokens minted before rotation shipped carry no jti; upgrade
            # them once (they cannot be denylisted, but they still expire).
            logger.warning(
                "Legacy refresh token without jti accepted for one-time upgrade",
                username=username,
            )

        # ROTATION complete: the consumed jti is denied until its own
        # expiry; mint a fresh pair (same family, new jti).
        new_refresh = create_refresh_token({"sub": user.username}, family_id=family_id)
        access_token = create_access_token(data={"sub": user.username})
        logger.info("Access token refreshed successfully", username=username)

        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            refresh_token=new_refresh,
        )

    except JWTError as e:
        logger.warning("Refresh token validation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except TokenStoreUnavailableError:
        # Fail CLOSED: without the denylist, reuse cannot be detected.
        logger.error("Token store unavailable - refusing refresh (fail closed)")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Token store unavailable",
        )


async def revoke_refresh_token(
    refresh_token: str,
    store: RefreshTokenStore | None = None,
) -> bool:
    """Explicitly revoke a refresh token (RFC 7009-style logout).

    Revoking the presented token also tombstones its family, so every
    descendant from earlier rotations dies with it. Invalid, expired or
    legacy (pre-``jti``) tokens are not errors: the call is idempotent
    and simply reports that nothing was revoked.
    """
    token_store = store if store is not None else get_refresh_token_store()
    try:
        try:
            payload = jwt.decode(
                refresh_token,
                settings.secret_key,
                algorithms=[settings.algorithm],
            )
        except JWTError:
            logger.info("Revoke requested for invalid refresh token - ignored")
            return False

        if payload.get("type") != "refresh":
            logger.info("Revoke requested for non-refresh token - ignored")
            return False

        jti = payload.get("jti")
        family_id = payload.get("fam")

        if not jti:
            logger.warning(
                "Legacy refresh token cannot be revoked server-side",
                username=payload.get("sub"),
            )
            return False

        remaining_seconds = max(1, int(payload.get("exp", time.time() + 1) - time.time()))
        await token_store.deny_jti(jti, ttl_seconds=remaining_seconds)
        if family_id:
            await token_store.revoke_family(family_id, ttl_seconds=FAMILY_REVOCATION_TTL_SECONDS)
        logger.info("Refresh token revoked", username=payload.get("sub"), jti=jti)
        return True
    except TokenStoreUnavailableError:
        logger.error("Token store unavailable during revoke")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Token store unavailable",
        )


async def get_qa_visual_principal(
    current_user: User = Depends(get_current_user),
) -> QAVisualPrincipal:
    """Map the authenticated user to the QA Visual access principal (S-1R).

    ``owner`` is the username reports are scoped to; ``is_superuser`` is
    the dashboard's existing admin role and bypasses the scoping.
    """
    # JWT edge (b): an empty identity must never scope reports to an
    # empty owner; reject it before it reaches the module.
    if not current_user.username or not current_user.username.strip():
        logger.warning("QA Visual principal rejected - empty username", user_id=current_user.id)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Authenticated user has no usable username to scope reports",
        )
    return QAVisualPrincipal(
        owner=current_user.username,
        is_admin=bool(current_user.is_superuser),
    )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    db: AsyncSession = Depends(get_db_session),
) -> Optional[User]:
    """Get current user if authenticated, None otherwise.

    This is useful for endpoints that work both for authenticated
    and anonymous users (e.g., feedback submission).
    """
    if credentials is None:
        logger.debug("No credentials provided - returning None for optional auth")
        return None

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        username: str = payload.get("sub")
        if username is None:
            return None
        # L-1: refresh tokens are anonymous on optional endpoints, same
        # rule as get_current_user.
        if payload.get("type") not in ACCESS_TOKEN_TYPES:
            logger.debug("Optional auth - non-access token type, returning None")
            return None

        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if user is None or not user.is_active:
            return None

        logger.debug("Optional auth - user found", username=username, user_id=user.id)
        return user

    except JWTError:
        logger.debug("Optional auth - invalid token, returning None")
        return None
