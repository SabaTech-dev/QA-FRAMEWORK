"""
Authentication Routes - OAuth, API Keys, Login
SECURITY FIX: Fixed API key circular dependency - BETA LAUNCH PREP 2026-03-27
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from database import get_db_session
from services.oauth_service import oauth_service, OAuthService
from services.api_key_service import api_key_service, get_user_from_api_key
from services.auth_service import login_for_access_token, get_current_user
from schemas import (
    LoginRequest, TokenResponse, OAuthLoginRequest, OAuthUrlResponse,
    ApiKeyCreate, ApiKeyResponse, UserCreate, UserResponse, RefreshTokenRequest
)
from models import User
from core.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# Email/Password Login
@router.post("/login", response_model=TokenResponse)
async def login(login_request: LoginRequest, db: AsyncSession = Depends(get_db_session)):
    return await login_for_access_token(login_request, db)


# User Registration
@router.post("/register", response_model=UserResponse)
async def register(
    user_create: UserCreate,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Register a new user with email/password
    
    Args:
        user_create: User registration data (email, username, password)
        
    Returns:
        UserResponse with user info (without password)
    """
    from services.user_service import create_user_service
    return await create_user_service(user_create, db)


# OAuth
@router.get("/oauth/{provider}/url", response_model=OAuthUrlResponse)
async def get_oauth_url(provider: str):
    import secrets
    state = secrets.token_urlsafe(16)
    
    if provider == "google":
        url = OAuthService.get_google_auth_url(state)
    elif provider == "github":
        url = OAuthService.get_github_auth_url(state)
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported provider: {provider}")
    
    return OAuthUrlResponse(provider=provider, authorization_url=url, state=state)


@router.post("/oauth/callback", response_model=TokenResponse)
async def oauth_callback(oauth_request: OAuthLoginRequest, db: AsyncSession = Depends(get_db_session)):
    return await oauth_service.oauth_login(db, oauth_request)


# API Keys
# SECURITY FIX: Changed from get_user_from_api_key to get_current_user to fix circular dependency
# Users must authenticate with JWT (login/OAuth) first, then can manage API keys
@router.post("/api-keys", response_model=ApiKeyResponse)
async def create_api_key(
    key_request: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create API key for current user (REQUIRES JWT authentication)"""
    return await api_key_service.create_api_key(db, current_user.id, key_request)


@router.get("/api-keys", response_model=List[ApiKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """List API keys for current user (REQUIRES JWT authentication)"""
    return await api_key_service.list_api_keys(db, current_user.id)


@router.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Revoke API key for current user (REQUIRES JWT authentication)"""
    success = await api_key_service.revoke_api_key(db, current_user.id, key_id)
    if not success:
        raise HTTPException(status_code=404, detail="API key not found")
    return {"message": "API key revoked successfully"}


# Session Management
@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db_session)
):
    """Refresh access token using refresh token"""
    from services.auth_service import refresh_access_token
    
    return await refresh_access_token(refresh_request.refresh_token, db)


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """Logout current user (client should discard token)"""
    logger.info("User logged out", user_id=current_user.id, username=current_user.username)
    # Note: JWT tokens are stateless, so logout is handled client-side by discarding the token
    # For more advanced logout (token blacklist), implement Redis-based token blacklist
    return {"message": "Logout successful. Please discard your tokens."}
