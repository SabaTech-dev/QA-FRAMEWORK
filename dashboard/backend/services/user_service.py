"""
User Service

Provides user management functionality including creation, listing, and retrieval.
"""

from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from models import User
from schemas import UserCreate, UserUpdate, UserResponse
from services.auth_service import PasswordTooLongError, hash_password
from core.logging_config import get_logger

# Initialize logger
logger = get_logger(__name__)


async def create_user_service(user_data: UserCreate, db: AsyncSession) -> User:
    """Create a new user"""
    logger.info("Creating new user", username=user_data.username, email=user_data.email)

    # Check if username exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        logger.warning(
            "User creation failed - username already exists",
            username=user_data.username,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Check if email exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        logger.warning("User creation failed - email already exists", email=user_data.email)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Create user (bcrypt 5: reject >72-byte passwords explicitly, PR #156)
    try:
        hashed_password = hash_password(user_data.password)
    except PasswordTooLongError as exc:
        logger.warning(
            "User creation failed - password exceeds 72-byte bcrypt limit",
            username=user_data.username,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password too long: bcrypt accepts a maximum of 72 bytes",
        ) from exc
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        is_active=user_data.is_active,
    )

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)

    logger.info("User created successfully", user_id=db_user.id, username=db_user.username)

    return db_user


async def list_users_service(
    skip: int = 0, limit: int = 100, db: AsyncSession = None
) -> List[User]:
    """List all users with pagination"""
    logger.debug("Listing users", skip=skip, limit=limit)

    result = await db.execute(
        select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
    )
    users = result.scalars().all()

    logger.info("Users listed successfully", count=len(users), skip=skip, limit=limit)

    return users


async def get_user_by_id(user_id: int, db: AsyncSession) -> User:
    """Get a user by ID"""
    logger.debug("Getting user by ID", user_id=user_id)

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        logger.error("User not found", user_id=user_id)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    logger.debug("User retrieved successfully", user_id=user_id, username=user.username)

    return user


async def update_user_service(user_id: int, user_update: UserUpdate, db: AsyncSession) -> User:
    """Update a user"""
    logger.info("Updating user", user_id=user_id)

    user = await get_user_by_id(user_id, db)

    # Update fields
    updated_fields = []
    if user_update.username is not None:
        logger.info(
            "Updating username",
            user_id=user_id,
            old_username=user.username,
            new_username=user_update.username,
        )
        user.username = user_update.username
        updated_fields.append("username")
    if user_update.email is not None:
        logger.info(
            "Updating email",
            user_id=user_id,
            old_email=user.email,
            new_email=user_update.email,
        )
        user.email = user_update.email
        updated_fields.append("email")
    if user_update.is_active is not None:
        logger.info(
            "Updating active status",
            user_id=user_id,
            old_status=user.is_active,
            new_status=user_update.is_active,
        )
        user.is_active = user_update.is_active
        updated_fields.append("is_active")

    await db.commit()
    await db.refresh(user)

    logger.info("User updated successfully", user_id=user_id, updated_fields=updated_fields)

    return user


async def delete_user_service(user_id: int, db: AsyncSession) -> None:
    """Delete a user (soft delete)"""
    logger.info("Soft deleting user", user_id=user_id)

    user = await get_user_by_id(user_id, db)

    logger.info(
        "Marking user as inactive",
        user_id=user_id,
        current_username=user.username,
        current_status=user.is_active,
    )

    user.is_active = False
    await db.commit()

    logger.info("User soft deleted successfully", user_id=user_id, username=user.username)
