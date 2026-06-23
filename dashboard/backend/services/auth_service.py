"""
Authentication Service

Provides JWT token generation and validation, password hashing, and user authentication.
"""

from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from config import settings
from models import User
from schemas import UserCreate, UserResponse, LoginRequest, TokenResponse
from database import get_db_session
from core.logging_config import get_logger, set_request_id

# Initialize logger
logger = get_logger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

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

    to_encode.update({"exp": expire})
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
    except JWTError as e:
        logger.warning("JWT validation failed", error=str(e))
        raise credentials_exception

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()

    if user is None:
        logger.warning("JWT validation failed - user not found", username=username)
        raise credentials_exception

    logger.debug("JWT token validated successfully", username=username, user_id=user.id)
    return user


async def require_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    """Authorize a superuser (admin).

    Builds on ``get_current_user`` so authentication (401) is enforced first,
    then enforces authorization (403) for non-admin accounts. Use this for
    endpoints that expose cross-user data (e.g. listing all users) to prevent
    Broken Access Control (OWASP A01:2021).
    """
    if not current_user.is_superuser:
        logger.warning(
            "Access denied - superuser privileges required",
            user_id=current_user.id,
            username=current_user.username,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions: superuser privileges required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return current_user


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


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a refresh token with longer expiry"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Default refresh token expiry: 7 days
        expire = datetime.utcnow() + timedelta(days=7)

    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    logger.debug("Refresh token created", expiry=expire.isoformat())
    return encoded_jwt


async def refresh_access_token(refresh_token: str, db: AsyncSession) -> TokenResponse:
    """Refresh access token using refresh token"""
    logger.info("Refreshing access token")

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

        # Create new access token
        access_token = create_access_token(data={"sub": user.username})
        logger.info("Access token refreshed successfully", username=username)

        return TokenResponse(access_token=access_token, token_type="bearer")

    except JWTError as e:
        logger.warning("Refresh token validation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
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

        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()

        if user is None or not user.is_active:
            return None

        logger.debug("Optional auth - user found", username=username, user_id=user.id)
        return user

    except JWTError:
        logger.debug("Optional auth - invalid token, returning None")
        return None
