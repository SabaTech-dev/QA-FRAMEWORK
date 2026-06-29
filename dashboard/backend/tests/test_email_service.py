"""
Unit tests for Email Service
"""

import pytest
pytest.importorskip('smtplib')
pytest.importorskip('email-validator')
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from services.email_service import (
    EmailService,
    EmailTemplate,
    send_beta_invitation,
    send_welcome_email,
    send_test_report,
    send_password_reset
)


@pytest.fixture
def email_service():
    """Create email service instance"""
    return EmailService()


@pytest.fixture
def mock_settings():
    """Mock settings"""
    with patch('services.email_service.settings') as mock:
        mock.SMTP_HOST = 'smtp.test.com'
        mock.SMTP_PORT = 587
        mock.SMTP_USER = 'test@test.com'
        mock.SMTP_PASSWORD = 'testpass'
        mock.FROM_EMAIL = 'test@test.com'
        mock.FROM_NAME = 'Test'
        mock.BASE_URL = 'https://test.com'
        yield mock


class TestEmailTemplates:
    """Test email templates"""
    
    def test_beta_invitation_template(self):
        """Test beta invitation template rendering"""
        html = EmailTemplate.BETA_INVITATION.format(
            name="John Doe",
            email="john@example.com",
            accept_url="https://example.com/accept",
            referral_code="BETA123",
            discord_url="https://discord.gg/example",
            unsubscribe_url="https://example.com/unsubscribe",
            privacy_url="https://example.com/privacy",
            year=2026
        )
        
        assert "John Doe" in html
        assert "BETA123" in html
        assert "https://example.com/accept" in html
        assert "2026" in html
    
    def test_welcome_template(self):
        """Test welcome template rendering"""
        html = EmailTemplate.WELCOME.format(
            name="Jane Doe",
            dashboard_url="https://dashboard.example.com",
            docs_url="https://docs.example.com",
            discord_url="https://discord.gg/example",
            year=2026
        )
        
        assert "Jane Doe" in html
        assert "dashboard.example.com" in html
        assert "2026" in html
    
    def test_test_report_template_success(self):
        """Test report template with high success rate"""
        html = EmailTemplate.TEST_REPORT.format(
            project_name="Test Project",
            execution_date="2026-02-27",
            total_tests=100,
            passed=95,
            failed=5,
            duration="2m 30s",
            success_rate=95.0,
            report_url="https://example.com/report",
            failed_tests_section="",
            header_color="#4CAF50",
            accent_color="#4CAF50",
            status_emoji="✅",
            settings_url="https://example.com/settings",
            year=2026
        )
        
        assert "Test Project" in html
        assert "95" in html
        assert "✅" in html
        assert "#4CAF50" in html
    
    def test_test_report_template_failure(self):
        """Test report template with low success rate"""
        html = EmailTemplate.TEST_REPORT.format(
            project_name="Test Project",
            execution_date="2026-02-27",
            total_tests=100,
            passed=50,
            failed=50,
            duration="2m 30s",
            success_rate=50.0,
            report_url="https://example.com/report",
            failed_tests_section="<h3>Failed Tests</h3>",
            header_color="#f44336",
            accent_color="#f44336",
            status_emoji="❌",
            settings_url="https://example.com/settings",
            year=2026
        )
        
        assert "Test Project" in html
        assert "50" in html
        assert "❌" in html
        assert "#f44336" in html
    
    def test_password_reset_template(self):
        """Test password reset template rendering"""
        html = EmailTemplate.PASSWORD_RESET.format(
            name="User",
            reset_url="https://example.com/reset?token=xxx",
            expires_in=24,
            year=2026
        )
        
        assert "User" in html
        assert "https://example.com/reset?token=xxx" in html
        assert "24" in html


class TestEmailService:
    """Test email service methods"""
    
    @pytest.mark.asyncio
    async def test_send_email_dev_mode(self, email_service, mock_settings):
        """Test sending email in development mode (no SMTP credentials)"""
        mock_settings.SMTP_USER = None
        mock_settings.SMTP_PASSWORD = None
        
        result = await email_service.send_email(
            to_email="test@example.com",
            subject="Test Subject",
            html_content="<html><body>Test</body></html>"
        )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_send_beta_invitation(self, email_service, mock_settings):
        """Test sending beta invitation"""
        with patch.object(email_service, 'send_email', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            result = await email_service.send_beta_invitation(
                to_email="test@example.com",
                name="John Doe",
                referral_code="BETA123"
            )
            
            assert result is True
            mock_send.assert_called_once()
            
            # Check subject contains expected content
            call_args = mock_send.call_args
            assert "Beta" in call_args[0][1]
    
    @pytest.mark.asyncio
    async def test_send_welcome_email(self, email_service, mock_settings):
        """Test sending welcome email"""
        with patch.object(email_service, 'send_email', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            result = await email_service.send_welcome_email(
                to_email="test@example.com",
                name="Jane Doe"
            )
            
            assert result is True
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_test_report(self, email_service, mock_settings):
        """Test sending test report"""
        with patch.object(email_service, 'send_email', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            result = await email_service.send_test_report(
                to_email="test@example.com",
                project_name="Test Project",
                execution_date="2026-02-27",
                total_tests=100,
                passed=95,
                failed=5,
                duration="2m 30s",
                report_url="https://example.com/report"
            )
            
            assert result is True
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_password_reset(self, email_service, mock_settings):
        """Test sending password reset email"""
        with patch.object(email_service, 'send_email', new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            result = await email_service.send_password_reset(
                to_email="test@example.com",
                name="User",
                reset_token="reset_token_123"
            )
            
            assert result is True
            mock_send.assert_called_once()


class TestConvenienceFunctions:
    """Test convenience functions"""
    
    @pytest.mark.asyncio
    async def test_send_beta_invitation_function(self):
        """Test beta invitation convenience function"""
        with patch('services.email_service.email_service.send_beta_invitation', new_callable=AsyncMock) as mock:
            mock.return_value = True
            
            result = await send_beta_invitation(
                to_email="test@example.com",
                name="John",
                referral_code="CODE123"
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_send_welcome_email_function(self):
        """Test welcome email convenience function"""
        with patch('services.email_service.email_service.send_welcome_email', new_callable=AsyncMock) as mock:
            mock.return_value = True
            
            result = await send_welcome_email(
                to_email="test@example.com",
                name="Jane"
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_send_test_report_function(self):
        """Test test report convenience function"""
        with patch('services.email_service.email_service.send_test_report', new_callable=AsyncMock) as mock:
            mock.return_value = True
            
            result = await send_test_report(
                to_email="test@example.com",
                project_name="Project",
                execution_date="2026-02-27",
                total_tests=10,
                passed=8,
                failed=2,
                duration="1m",
                report_url="https://example.com"
            )
            
            assert result is True
    
    @pytest.mark.asyncio
    async def test_send_password_reset_function(self):
        """Test password reset convenience function"""
        with patch('services.email_service.email_service.send_password_reset', new_callable=AsyncMock) as mock:
            mock.return_value = True
            
            result = await send_password_reset(
                to_email="test@example.com",
                name="User",
                reset_token="token123"
            )
            
            assert result is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
