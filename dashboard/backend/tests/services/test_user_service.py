"""
Unit tests for user_service.py

Tests all user management functions with mocked database sessions.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))


class TestCreateUserService:
    """Tests for create_user_service function."""

    @pytest.mark.asyncio
    async def test_create_user_success(self):
        """Test successful user creation."""
        from services.user_service import create_user_service

        mock_db = AsyncMock()
        mock_user_data = MagicMock()
        mock_user_data.username = "testuser"
        mock_user_data.email = "test@example.com"
        mock_user_data.password = "password123"
        mock_user_data.is_active = True

        # Mock: no existing user with same username or email
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        # Mock hash_password
        with patch("services.user_service.hash_password", return_value="hashed_pw"):
            result = await create_user_service(mock_user_data, mock_db)

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_duplicate_username(self):
        """Test user creation fails with duplicate username."""
        from services.user_service import create_user_service

        mock_db = AsyncMock()
        mock_user_data = MagicMock()
        mock_user_data.username = "existinguser"
        mock_user_data.email = "new@example.com"

        # Mock: existing user with same username
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = MagicMock()  # User exists
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await create_user_service(mock_user_data, mock_db)

        assert exc_info.value.status_code == 400
        assert "Username already registered" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_user_duplicate_email(self):
        """Test user creation fails with duplicate email."""
        from services.user_service import create_user_service

        mock_db = AsyncMock()
        mock_user_data = MagicMock()
        mock_user_data.username = "newuser"
        mock_user_data.email = "existing@example.com"

        # Mock: first check (username) passes, second check (email) fails
        mock_result_no_user = MagicMock()
        mock_result_no_user.scalar_one_or_none.return_value = None

        mock_result_existing_email = MagicMock()
        mock_result_existing_email.scalar_one_or_none.return_value = MagicMock()

        mock_db.execute.side_effect = [mock_result_no_user, mock_result_existing_email]

        with pytest.raises(HTTPException) as exc_info:
            await create_user_service(mock_user_data, mock_db)

        assert exc_info.value.status_code == 400
        assert "Email already registered" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_create_user_inactive(self):
        """Test creating an inactive user."""
        from services.user_service import create_user_service

        mock_db = AsyncMock()
        mock_user_data = MagicMock()
        mock_user_data.username = "inactiveuser"
        mock_user_data.email = "inactive@example.com"
        mock_user_data.password = "password"
        mock_user_data.is_active = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with patch("services.user_service.hash_password", return_value="hashed"):
            await create_user_service(mock_user_data, mock_db)

        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_rejects_password_over_72_bytes(self):
        """bcrypt 5 adaptation: >72-byte passwords get a controlled 400."""
        from services.user_service import create_user_service

        mock_db = AsyncMock()
        mock_user_data = MagicMock()
        mock_user_data.username = "longpwduser"
        mock_user_data.email = "long@example.com"
        mock_user_data.password = "x" * 73
        mock_user_data.is_active = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await create_user_service(mock_user_data, mock_db)

        assert exc_info.value.status_code == 400
        assert "72" in str(exc_info.value.detail)
        mock_db.add.assert_not_called()


class TestListUsersService:
    """Tests for list_users_service function."""

    @pytest.mark.asyncio
    async def test_list_users_default_params(self):
        """Test listing users with default parameters."""
        from services.user_service import list_users_service

        mock_db = AsyncMock()
        mock_users = [MagicMock(), MagicMock(), MagicMock()]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_users
        mock_db.execute.return_value = mock_result

        result = await list_users_service(db=mock_db)

        assert result == mock_users
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_list_users_with_pagination(self):
        """Test listing users with skip and limit."""
        from services.user_service import list_users_service

        mock_db = AsyncMock()
        mock_users = [MagicMock()]

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = mock_users
        mock_db.execute.return_value = mock_result

        result = await list_users_service(skip=10, limit=5, db=mock_db)

        assert result == mock_users
        mock_db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_list_users_empty(self):
        """Test listing when no users exist."""
        from services.user_service import list_users_service

        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await list_users_service(db=mock_db)

        assert result == []


class TestGetUserById:
    """Tests for get_user_by_id function."""

    @pytest.mark.asyncio
    async def test_get_user_success(self):
        """Test successfully getting a user by ID."""
        from services.user_service import get_user_by_id

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "testuser"

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        result = await get_user_by_id(1, mock_db)

        assert result == mock_user

    @pytest.mark.asyncio
    async def test_get_user_not_found(self):
        """Test 404 when user not found."""
        from services.user_service import get_user_by_id

        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await get_user_by_id(999, mock_db)

        assert exc_info.value.status_code == 404
        assert "User not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_user_by_id_zero(self):
        """Test edge case: user ID = 0."""
        from services.user_service import get_user_by_id

        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await get_user_by_id(0, mock_db)

        assert exc_info.value.status_code == 404


class TestUpdateUserService:
    """Tests for update_user_service function."""

    @pytest.mark.asyncio
    async def test_update_username(self):
        """Test updating a user's username."""
        from services.user_service import update_user_service

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.username = "oldname"
        mock_user.email = "test@example.com"
        mock_user.is_active = True

        mock_user_update = MagicMock()
        mock_user_update.username = "newname"
        mock_user_update.email = None
        mock_user_update.is_active = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        await update_user_service(1, mock_user_update, mock_db)

        assert mock_user.username == "newname"
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_email(self):
        """Test updating a user's email."""
        from services.user_service import update_user_service

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.username = "testuser"
        mock_user.email = "old@example.com"
        mock_user.is_active = True

        mock_user_update = MagicMock()
        mock_user_update.username = None
        mock_user_update.email = "new@example.com"
        mock_user_update.is_active = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        await update_user_service(1, mock_user_update, mock_db)

        assert mock_user.email == "new@example.com"

    @pytest.mark.asyncio
    async def test_update_active_status(self):
        """Test updating a user's active status."""
        from services.user_service import update_user_service

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.is_active = True

        mock_user_update = MagicMock()
        mock_user_update.username = None
        mock_user_update.email = None
        mock_user_update.is_active = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        await update_user_service(1, mock_user_update, mock_db)

        assert mock_user.is_active == False

    @pytest.mark.asyncio
    async def test_update_user_not_found(self):
        """Test update fails when user not found."""
        from services.user_service import update_user_service

        mock_db = AsyncMock()
        mock_user_update = MagicMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await update_user_service(999, mock_user_update, mock_db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_update_no_changes(self):
        """Test update with no fields to change."""
        from services.user_service import update_user_service

        mock_db = AsyncMock()
        mock_user = MagicMock()

        mock_user_update = MagicMock()
        mock_user_update.username = None
        mock_user_update.email = None
        mock_user_update.is_active = None

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        await update_user_service(1, mock_user_update, mock_db)

        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_all_fields(self):
        """Test updating all fields at once."""
        from services.user_service import update_user_service

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.username = "old"
        mock_user.email = "old@e.com"
        mock_user.is_active = True

        mock_user_update = MagicMock()
        mock_user_update.username = "new"
        mock_user_update.email = "new@e.com"
        mock_user_update.is_active = False

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        await update_user_service(1, mock_user_update, mock_db)

        assert mock_user.username == "new"
        assert mock_user.email == "new@e.com"
        assert mock_user.is_active == False


class TestDeleteUserService:
    """Tests for delete_user_service function."""

    @pytest.mark.asyncio
    async def test_delete_user_success(self):
        """Test successful user soft delete."""
        from services.user_service import delete_user_service

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.is_active = True

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        await delete_user_service(1, mock_db)

        assert mock_user.is_active == False
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self):
        """Test delete fails when user not found."""
        from services.user_service import delete_user_service

        mock_db = AsyncMock()

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await delete_user_service(999, mock_db)

        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_already_inactive_user(self):
        """Test soft-deleting a user that's already inactive."""
        from services.user_service import delete_user_service

        mock_db = AsyncMock()
        mock_user = MagicMock()
        mock_user.is_active = False  # Already inactive

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_db.execute.return_value = mock_result

        # Should still work, just sets is_active = False again
        await delete_user_service(1, mock_db)

        assert mock_user.is_active == False
        mock_db.commit.assert_called_once()
