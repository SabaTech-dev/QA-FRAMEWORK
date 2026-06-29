"""
Unit Tests for OAuth Service

Tests Google and GitHub OAuth integration with comprehensive mocking.
"""
import pytest
pytest.importorskip('fastapi')
pytest.importorskip('httpx')
pytest.importorskip('asyncpg')
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi import HTTPException
import httpx

from services.oauth_service import (
    OAuthService,
    oauth_service
)
from models import User
from schemas import OAuthLoginRequest, OAuthProvider, TokenResponse


@pytest.fixture
def mock_db():
    """Mock database session"""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.add = Mock()
    db.refresh = AsyncMock()
    db.execute = AsyncMock()
    return db


@pytest.fixture
def mock_google_user_info():
    """Mock Google user info response"""
    return {
        "id": "google_123",
        "email": "test@gmail.com",
        "name": "Test User",
        "picture": "https://example.com/photo.jpg"
    }


@pytest.fixture
def mock_github_user_info():
    """Mock GitHub user info response"""
    return {
        "id": 456789,
        "login": "testuser",
        "name": "Test User",
        "email": None,  # GitHub may not return email in user info
        "avatar_url": "https://example.com/avatar.jpg"
    }


@pytest.fixture
def mock_github_emails():
    """Mock GitHub emails response"""
    return [
        {"email": "test@example.com", "primary": True, "verified": True},
        {"email": "test@github.com", "primary": False, "verified": True}
    ]


class TestGetGoogleAuthUrl:
    """Tests for Google OAuth URL generation"""
    
    def test_get_google_auth_url_basic(self):
        """Test basic Google auth URL generation"""
        state = "random_state_123"
        url = OAuthService.get_google_auth_url(state)
        
        assert "accounts.google.com/o/oauth2/v2/auth" in url
        assert "client_id=" in url
        assert "redirect_uri=" in url
        assert "response_type=code" in url
        assert "scope=" in url
        assert "openid" in url
        assert "email" in url
        assert "profile" in url
        assert f"state={state}" in url
        assert "access_type=offline" in url
        assert "prompt=consent" in url
    
    def test_get_google_auth_url_includes_all_params(self):
        """Test Google auth URL includes all required parameters"""
        state = "test_state"
        url = OAuthService.get_google_auth_url(state)
        
        # Verify all OAuth parameters present
        assert "client_id" in url
        assert "redirect_uri" in url
        assert "response_type" in url
        assert "scope" in url
        assert "state" in url
        assert "access_type" in url
        assert "prompt" in url
    
    def test_get_google_auth_url_state_injection(self):
        """Test state parameter is properly included"""
        state = "unique_state_token"
        url = OAuthService.get_google_auth_url(state)
        
        # State should be in URL
        assert f"state={state}" in url


class TestGetGithubAuthUrl:
    """Tests for GitHub OAuth URL generation"""
    
    def test_get_github_auth_url_basic(self):
        """Test basic GitHub auth URL generation"""
        state = "random_state_456"
        url = OAuthService.get_github_auth_url(state)
        
        assert "github.com/login/oauth/authorize" in url
        assert "client_id=" in url
        assert "redirect_uri=" in url
        assert "scope=user:email" in url
        assert f"state={state}" in url
    
    def test_get_github_auth_url_includes_all_params(self):
        """Test GitHub auth URL includes all required parameters"""
        state = "test_state"
        url = OAuthService.get_github_auth_url(state)
        
        assert "client_id" in url
        assert "redirect_uri" in url
        assert "scope" in url
        assert "state" in url


class TestExchangeGoogleCode:
    """Tests for Google code exchange"""
    
    @pytest.mark.asyncio
    async def test_exchange_google_code_success(self):
        """Test successful Google code exchange"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "google_access_token",
            "token_type": "Bearer",
            "expires_in": 3600
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await OAuthService.exchange_google_code("test_code")
            
            assert result["access_token"] == "google_access_token"
            assert result["token_type"] == "Bearer"
    
    @pytest.mark.asyncio
    async def test_exchange_google_code_failure(self):
        """Test Google code exchange failure"""
        mock_response = Mock()
        mock_response.status_code = 400
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            with pytest.raises(HTTPException) as exc_info:
                await OAuthService.exchange_google_code("invalid_code")
            
            assert exc_info.value.status_code == 400
            assert "Google OAuth failed" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_exchange_google_code_posts_correct_data(self):
        """Test Google exchange posts correct data"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"access_token": "token"}
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            await OAuthService.exchange_google_code("test_code")
            
            # Verify post called with correct params
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "https://oauth2.googleapis.com/token"
            
            data = call_args[1]["data"]
            assert data["code"] == "test_code"
            assert data["grant_type"] == "authorization_code"


class TestExchangeGithubCode:
    """Tests for GitHub code exchange"""
    
    @pytest.mark.asyncio
    async def test_exchange_github_code_success(self):
        """Test successful GitHub code exchange"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "github_access_token",
            "token_type": "bearer",
            "scope": "user:email"
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await OAuthService.exchange_github_code("test_code")
            
            assert result["access_token"] == "github_access_token"
    
    @pytest.mark.asyncio
    async def test_exchange_github_code_failure(self):
        """Test GitHub code exchange failure"""
        mock_response = Mock()
        mock_response.status_code = 400
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            with pytest.raises(HTTPException) as exc_info:
                await OAuthService.exchange_github_code("invalid_code")
            
            assert exc_info.value.status_code == 400
            assert "GitHub OAuth failed" in exc_info.value.detail


class TestGetGoogleUserInfo:
    """Tests for Google user info retrieval"""
    
    @pytest.mark.asyncio
    async def test_get_google_user_info_success(self, mock_google_user_info):
        """Test successful Google user info retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_google_user_info
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            result = await OAuthService.get_google_user_info("google_token")
            
            assert result["email"] == "test@gmail.com"
            assert result["name"] == "Test User"
            assert result["id"] == "google_123"
    
    @pytest.mark.asyncio
    async def test_get_google_user_info_failure(self):
        """Test Google user info retrieval failure"""
        mock_response = Mock()
        mock_response.status_code = 401
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            with pytest.raises(HTTPException) as exc_info:
                await OAuthService.get_google_user_info("invalid_token")
            
            assert exc_info.value.status_code == 400
            assert "Failed to get Google user info" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_google_user_info_uses_bearer_token(self, mock_google_user_info):
        """Test Google user info uses Bearer token"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_google_user_info
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            await OAuthService.get_google_user_info("test_token")
            
            # Verify Authorization header
            call_args = mock_client.get.call_args
            headers = call_args[1]["headers"]
            assert headers["Authorization"] == "Bearer test_token"


class TestGetGithubUserInfo:
    """Tests for GitHub user info retrieval"""
    
    @pytest.mark.asyncio
    async def test_get_github_user_info_success(self, mock_github_user_info, mock_github_emails):
        """Test successful GitHub user info retrieval"""
        mock_user_response = Mock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = mock_github_user_info
        
        mock_email_response = Mock()
        mock_email_response.status_code = 200
        mock_email_response.json.return_value = mock_github_emails
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(side_effect=[mock_user_response, mock_email_response])
            mock_client_class.return_value = mock_client
            
            result = await OAuthService.get_github_user_info("github_token")
            
            assert result["login"] == "testuser"
            assert result["email"] == "test@example.com"  # Primary email
    
    @pytest.mark.asyncio
    async def test_get_github_user_info_failure(self):
        """Test GitHub user info retrieval failure"""
        mock_response = Mock()
        mock_response.status_code = 401
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client
            
            with pytest.raises(HTTPException) as exc_info:
                await OAuthService.get_github_user_info("invalid_token")
            
            assert exc_info.value.status_code == 400
            assert "Failed to get GitHub user info" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_get_github_user_info_no_primary_email(self, mock_github_user_info):
        """Test GitHub user info when no primary email"""
        mock_user_response = Mock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = mock_github_user_info
        
        mock_email_response = Mock()
        mock_email_response.status_code = 200
        mock_email_response.json.return_value = []  # No emails
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(side_effect=[mock_user_response, mock_email_response])
            mock_client_class.return_value = mock_client
            
            result = await OAuthService.get_github_user_info("github_token")
            
            # Email should remain None
            assert result.get("email") is None
    
    @pytest.mark.asyncio
    async def test_get_github_user_info_email_endpoint_fails(self, mock_github_user_info):
        """Test GitHub user info when email endpoint fails"""
        mock_user_response = Mock()
        mock_user_response.status_code = 200
        mock_user_response.json.return_value = mock_github_user_info
        
        mock_email_response = Mock()
        mock_email_response.status_code = 404  # Email endpoint fails
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client.get = AsyncMock(side_effect=[mock_user_response, mock_email_response])
            mock_client_class.return_value = mock_client
            
            result = await OAuthService.get_github_user_info("github_token")
            
            # Should still return user info without email
            assert result["login"] == "testuser"


class TestOAuthLogin:
    """Tests for OAuth login flow"""
    
    @pytest.mark.asyncio
    async def test_oauth_login_google_new_user(self, mock_db, mock_google_user_info):
        """Test OAuth login with Google for new user"""
        oauth_request = OAuthLoginRequest(
            provider=OAuthProvider.google,
            code="google_code"
        )
        
        # Mock code exchange
        mock_tokens = {"access_token": "google_token"}
        
        # Mock database query - no existing user
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute.return_value = mock_result
        
        with patch.object(OAuthService, 'exchange_google_code', return_value=mock_tokens), \
             patch.object(OAuthService, 'get_google_user_info', return_value=mock_google_user_info), \
             patch('services.oauth_service.create_access_token', return_value="jwt_token"), \
             patch('services.oauth_service.hash_password', return_value="hashed_pwd"):
            
            result = await OAuthService.oauth_login(mock_db, oauth_request, tenant_id="tenant_123")
            
            assert isinstance(result, TokenResponse)
            assert result.access_token == "jwt_token"
            assert result.token_type == "bearer"
            
            # Verify user was added
            mock_db.add.assert_called_once()
            mock_db.commit.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_oauth_login_google_existing_user(self, mock_db, mock_google_user_info):
        """Test OAuth login with Google for existing user"""
        oauth_request = OAuthLoginRequest(
            provider=OAuthProvider.google,
            code="google_code"
        )
        
        # Mock existing user
        existing_user = User(
            id=1,
            email="test@gmail.com",
            username="test",
            hashed_password="hashed"
        )
        
        mock_tokens = {"access_token": "google_token"}
        
        # Mock database query - existing user
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=existing_user)
        mock_db.execute.return_value = mock_result
        
        with patch.object(OAuthService, 'exchange_google_code', return_value=mock_tokens), \
             patch.object(OAuthService, 'get_google_user_info', return_value=mock_google_user_info), \
             patch('services.oauth_service.create_access_token', return_value="jwt_token"):
            
            result = await OAuthService.oauth_login(mock_db, oauth_request)
            
            assert isinstance(result, TokenResponse)
            assert result.access_token == "jwt_token"
            
            # Verify new user was NOT added
            mock_db.add.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_oauth_login_github_new_user(self, mock_db, mock_github_user_info, mock_github_emails):
        """Test OAuth login with GitHub for new user"""
        oauth_request = OAuthLoginRequest(
            provider=OAuthProvider.github,
            code="github_code"
        )
        
        # Add email to GitHub user info
        mock_github_user_info["email"] = "test@example.com"
        
        mock_tokens = {"access_token": "github_token"}
        
        # Mock database query - no existing user
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute.return_value = mock_result
        
        with patch.object(OAuthService, 'exchange_github_code', return_value=mock_tokens), \
             patch.object(OAuthService, 'get_github_user_info', return_value=mock_github_user_info), \
             patch('services.oauth_service.create_access_token', return_value="jwt_token"), \
             patch('services.oauth_service.hash_password', return_value="hashed_pwd"):
            
            result = await OAuthService.oauth_login(mock_db, oauth_request)
            
            assert isinstance(result, TokenResponse)
            assert result.access_token == "jwt_token"
            
            # Verify user was added
            mock_db.add.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_oauth_login_unsupported_provider(self, mock_db):
        """Test OAuth login with unsupported provider"""
        # Pydantic will validate the provider enum before the service is called
        # So we test the validation error
        with pytest.raises(Exception) as exc_info:
            oauth_request = OAuthLoginRequest(
                provider="linkedin",  # Unsupported
                code="linkedin_code"
            )
        
        # Should raise a validation error
        assert "provider" in str(exc_info.value).lower()
    
    @pytest.mark.asyncio
    async def test_oauth_login_no_email(self, mock_db, mock_github_user_info):
        """Test OAuth login when no email provided"""
        oauth_request = OAuthLoginRequest(
            provider=OAuthProvider.github,
            code="github_code"
        )
        
        # No email in user info
        mock_github_user_info["email"] = None
        
        mock_tokens = {"access_token": "github_token"}
        
        with patch.object(OAuthService, 'exchange_github_code', return_value=mock_tokens), \
             patch.object(OAuthService, 'get_github_user_info', return_value=mock_github_user_info):
            
            with pytest.raises(HTTPException) as exc_info:
                await OAuthService.oauth_login(mock_db, oauth_request)
            
            assert exc_info.value.status_code == 400
            assert "Email not provided" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_oauth_login_with_tenant(self, mock_db, mock_google_user_info):
        """Test OAuth login with tenant_id"""
        oauth_request = OAuthLoginRequest(
            provider=OAuthProvider.google,
            code="google_code"
        )
        
        mock_tokens = {"access_token": "google_token"}
        
        # Mock database query - no existing user
        mock_result = AsyncMock()
        mock_result.scalar_one_or_none = Mock(return_value=None)
        mock_db.execute.return_value = mock_result
        
        created_user = None
        
        def capture_user(user):
            nonlocal created_user
            created_user = user
        
        mock_db.add.side_effect = capture_user
        
        with patch.object(OAuthService, 'exchange_google_code', return_value=mock_tokens), \
             patch.object(OAuthService, 'get_google_user_info', return_value=mock_google_user_info), \
             patch('services.oauth_service.create_access_token', return_value="jwt_token"), \
             patch('services.oauth_service.hash_password', return_value="hashed_pwd"):
            
            result = await OAuthService.oauth_login(mock_db, oauth_request, tenant_id="tenant_123")
            
            # Verify tenant_id was set
            assert created_user.tenant_id == "tenant_123"


class TestOAuthServiceInstance:
    """Tests for OAuth service instance"""
    
    def test_oauth_service_instance_exists(self):
        """Test oauth_service instance is created"""
        assert oauth_service is not None
        assert isinstance(oauth_service, OAuthService)
    
    def test_oauth_service_has_required_methods(self):
        """Test oauth_service has all required methods"""
        assert hasattr(oauth_service, 'get_google_auth_url')
        assert hasattr(oauth_service, 'get_github_auth_url')
        assert hasattr(oauth_service, 'exchange_google_code')
        assert hasattr(oauth_service, 'exchange_github_code')
        assert hasattr(oauth_service, 'get_google_user_info')
        assert hasattr(oauth_service, 'get_github_user_info')
        assert hasattr(oauth_service, 'oauth_login')


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=services/oauth_service", "--cov-report=term-missing"])
