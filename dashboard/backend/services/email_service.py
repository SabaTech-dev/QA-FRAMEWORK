"""
Email Service

Provides email sending capabilities with HTML/text templates for:
- Beta tester invitations
- Welcome emails
- Password reset
- Notification alerts
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import logging

from config import settings
from core.logging_config import get_logger

logger = get_logger(__name__)


class EmailTemplate:
    """Email template constants"""
    
    # Beta Tester Invitation
    BETA_INVITATION = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
        .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
        .features {{ background: white; padding: 20px; border-radius: 5px; margin: 20px 0; }}
        .feature-item {{ margin: 10px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Welcome to QA-FRAMEWORK Beta!</h1>
            <p>You've been selected to shape the future of automated testing</p>
        </div>
        <div class="content">
            <h2>Hi {name},</h2>
            <p>Congratulations! You've been invited to join the QA-FRAMEWORK Beta Program. We're excited to have you on board.</p>
            
            <div class="features">
                <h3>🎁 What You Get:</h3>
                <div class="feature-item">✅ <strong>Early Access</strong> - Be the first to try our AI-powered testing features</div>
                <div class="feature-item">✅ <strong>Free Pro Plan</strong> - 3 months of Pro features ($297 value)</div>
                <div class="feature-item">✅ <strong>Priority Support</strong> - Direct line to our engineering team</div>
                <div class="feature-item">✅ <strong>Shape the Product</strong> - Your feedback drives our roadmap</div>
            </div>
            
            <p style="text-align: center; margin: 30px 0;">
                <a href="{accept_url}" class="button">Accept Beta Invitation</a>
            </p>
            
            <p><strong>What happens next:</strong></p>
            <ol>
                <li>Click the button above to activate your beta account</li>
                <li>Complete your profile and set up your first project</li>
                <li>Start testing with AI-powered features</li>
                <li>Share your feedback to help us improve</li>
            </ol>
            
            <p><strong>Beta Program Duration:</strong> 90 days</p>
            <p><strong>Your Unique Referral Code:</strong> <code style="background: #e0e0e0; padding: 5px 10px; border-radius: 3px;">{referral_code}</code></p>
            
            <p>Questions? Reply to this email or join our <a href="{discord_url}">Discord community</a>.</p>
            
            <p>Best regards,<br>The QA-FRAMEWORK Team</p>
        </div>
        <div class="footer">
            <p>© {year} QA-FRAMEWORK. All rights reserved.</p>
            <p>This email was sent to {email}</p>
            <p><a href="{unsubscribe_url}">Unsubscribe</a> | <a href="{privacy_url}">Privacy Policy</a></p>
        </div>
    </div>
</body>
</html>
"""
    
    # Welcome Email
    WELCOME = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #4CAF50; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .button {{ display: inline-block; background: #4CAF50; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
        .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
        .quick-start {{ background: white; padding: 20px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #4CAF50; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 Welcome to QA-FRAMEWORK!</h1>
            <p>Your journey to better testing starts now</p>
        </div>
        <div class="content">
            <h2>Welcome, {name}!</h2>
            <p>Thanks for joining QA-FRAMEWORK. You're now part of a community of developers who believe testing should be easy, fast, and intelligent.</p>
            
            <div class="quick-start">
                <h3>🚀 Quick Start Guide:</h3>
                <ol>
                    <li><strong>Create your first project</strong> - Organize your tests in one place</li>
                    <li><strong>Connect your repository</strong> - Link GitHub, GitLab, or Bitbucket</li>
                    <li><strong>Generate your first test</strong> - Use AI to create tests from requirements</li>
                    <li><strong>Run tests automatically</strong> - Set up CI/CD integration</li>
                </ol>
            </div>
            
            <p style="text-align: center; margin: 30px 0;">
                <a href="{dashboard_url}" class="button">Go to Dashboard</a>
            </p>
            
            <p><strong>Need help?</strong></p>
            <ul>
                <li>📖 <a href="{docs_url}">Documentation</a></li>
                <li>💬 <a href="{discord_url}">Community Discord</a></li>
                <li>📧 <a href="mailto:support@qa-framework.io">Email Support</a></li>
            </ul>
            
            <p>Happy testing!</p>
            <p>The QA-FRAMEWORK Team</p>
        </div>
        <div class="footer">
            <p>© {year} QA-FRAMEWORK. All rights reserved.</p>
            <p>You're receiving this because you signed up at qa-framework.io</p>
        </div>
    </div>
</body>
</html>
"""
    
    # Test Execution Report
    TEST_REPORT = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: {header_color}; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .stats {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin: 20px 0; }}
        .stat {{ background: white; padding: 15px; border-radius: 5px; text-align: center; }}
        .stat-number {{ font-size: 24px; font-weight: bold; color: {accent_color}; }}
        .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
        .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{status_emoji} Test Execution Report</h1>
            <p>{project_name} - {execution_date}</p>
        </div>
        <div class="content">
            <div class="stats">
                <div class="stat">
                    <div class="stat-number">{total_tests}</div>
                    <div>Total Tests</div>
                </div>
                <div class="stat">
                    <div class="stat-number" style="color: #4CAF50;">{passed}</div>
                    <div>Passed</div>
                </div>
                <div class="stat">
                    <div class="stat-number" style="color: #f44336;">{failed}</div>
                    <div>Failed</div>
                </div>
            </div>
            
            <p><strong>Duration:</strong> {duration}</p>
            <p><strong>Success Rate:</strong> {success_rate}%</p>
            
            {failed_tests_section}
            
            <p style="text-align: center; margin: 30px 0;">
                <a href="{report_url}" class="button">View Full Report</a>
            </p>
            
            <p>The QA-FRAMEWORK Team</p>
        </div>
        <div class="footer">
            <p>© {year} QA-FRAMEWORK. All rights reserved.</p>
            <p><a href="{settings_url}">Notification Settings</a></p>
        </div>
    </div>
</body>
</html>
"""
    
    # Password Reset
    PASSWORD_RESET = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: #ff9800; color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .button {{ display: inline-block; background: #ff9800; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
        .warning {{ background: #fff3cd; border-left: 4px solid #ff9800; padding: 15px; margin: 20px 0; }}
        .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔐 Password Reset Request</h1>
        </div>
        <div class="content">
            <h2>Hi {name},</h2>
            <p>We received a request to reset your password for your QA-FRAMEWORK account.</p>
            
            <p style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" class="button">Reset Password</a>
            </p>
            
            <div class="warning">
                <strong>⚠️ Security Notice:</strong>
                <ul>
                    <li>This link expires in {expires_in} hours</li>
                    <li>If you didn't request this reset, ignore this email</li>
                    <li>Never share this link with anyone</li>
                </ul>
            </div>
            
            <p>The QA-FRAMEWORK Team</p>
        </div>
        <div class="footer">
            <p>© {year} QA-FRAMEWORK. All rights reserved.</p>
        </div>
    </div>
</body>
</html>
"""


    # Waitlist Approved Template
    WAITLIST_APPROVED = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; text-align: center; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .button {{ display: inline-block; background: #667eea; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
        .footer {{ text-align: center; margin-top: 20px; color: #666; font-size: 12px; }}
        .features {{ background: white; padding: 20px; border-radius: 5px; margin: 20px 0; }}
        .limits {{ background: #fff3cd; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #ffc107; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎉 You're In! Welcome to QA-FRAMEWORK</h1>
            <p>Your waitlist spot has been upgraded to full beta access</p>
        </div>
        <div class="content">
            <h2>Hi {name},</h2>
            <p>Great news! You've been approved for QA-FRAMEWORK beta access. We're excited to have you on board.</p>

            <div class="features">
                <h3>🚀 What You Get:</h3>
                <div class="feature-item">✅ <strong>AI Self-Healing Tests</strong> - Tests that fix themselves</div>
                <div class="feature-item">✅ <strong>AI Test Generation</strong> - Generate tests from requirements</div>
                <div class="feature-item">✅ <strong>Flaky Detection</strong> - Automatic flaky test quarantine</div>
                <div class="feature-item">✅ <strong>Dashboard & Analytics</strong> - Comprehensive test insights</div>
            </div>

            <div class="limits">
                <strong>⚡ Beta Limits:</strong>
                <ul>
                    <li>Up to <strong>5 scans</strong> per day</li>
                    <li><strong>1 concurrent</strong> scan at a time</li>
                    <li><strong>5-minute</strong> scan timeout</li>
                    <li><strong>100MB</strong> storage per project</li>
                </ul>
            </div>

            <p style="text-align: center; margin: 30px 0;">
                <a href="{dashboard_url}" class="button">Go to Dashboard</a>
            </p>

            <p><strong>Get started:</strong></p>
            <ol>
                <li>Click the button above to access your dashboard</li>
                <li>Create your first test project</li>
                <li>Connect your repository or start testing</li>
                <li>Share feedback to help shape the product</li>
            </ol>

            <p>Questions? Join our <a href="{discord_url}">Discord community</a> or reply to this email.</p>

            <p>Happy testing!<br>The QA-FRAMEWORK Team</p>
        </div>
        <div class="footer">
            <p>&copy; {year} QA-FRAMEWORK. All rights reserved.</p>
            <p>Sent to {email}</p>
        </div>
    </div>
</body>
</html>
"""


class EmailService:
    """Email service for sending emails with templates"""
    
    def __init__(self):
        self.smtp_host = getattr(settings, 'SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = getattr(settings, 'SMTP_PORT', 587)
        self.smtp_user = getattr(settings, 'SMTP_USER', None)
        self.smtp_password = getattr(settings, 'SMTP_PASSWORD', None)
        self.from_email = getattr(settings, 'FROM_EMAIL', 'noreply@qa-framework.io')
        self.from_name = getattr(settings, 'FROM_NAME', 'QA-FRAMEWORK')
        self.base_url = getattr(settings, 'BASE_URL', 'https://qa-framework.io')
        self.year = datetime.now().year
    
    async def send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Send an email
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content
            text_content: Plain text content (optional)
            attachments: List of attachments (optional)
        
        Returns:
            bool: True if sent successfully
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{self.from_name} <{self.from_email}>"
            msg['To'] = to_email
            
            # Add text content
            if text_content:
                msg.attach(MIMEText(text_content, 'plain'))
            
            # Add HTML content
            msg.attach(MIMEText(html_content, 'html'))
            
            # Add attachments
            if attachments:
                for attachment in attachments:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment['content'])
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f"attachment; filename= {attachment['filename']}"
                    )
                    msg.attach(part)
            
            # Send email
            if self.smtp_user and self.smtp_password:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.smtp_user, self.smtp_password)
                    server.send_message(msg)
                    logger.info(f"Email sent successfully to {to_email}")
            else:
                # Log email for development
                logger.info(f"Email (dev mode): To={to_email}, Subject={subject}")
                logger.debug(f"Email content preview: {html_content[:200]}...")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    async def send_beta_invitation(
        self,
        to_email: str,
        name: str,
        referral_code: str,
        accept_url: Optional[str] = None
    ) -> bool:
        """Send beta tester invitation email"""
        accept_url = accept_url or f"{self.base_url}/beta/accept?code={referral_code}"
        
        html = EmailTemplate.BETA_INVITATION.format(
            name=name,
            email=to_email,
            accept_url=accept_url,
            referral_code=referral_code,
            discord_url=f"{self.base_url}/discord",
            unsubscribe_url=f"{self.base_url}/unsubscribe?email={to_email}",
            privacy_url=f"{self.base_url}/privacy",
            year=self.year
        )
        
        subject = "🚀 You're Invited! Join the QA-FRAMEWORK Beta Program"
        
        return await self.send_email(to_email, subject, html)
    
    async def send_welcome_email(
        self,
        to_email: str,
        name: str
    ) -> bool:
        """Send welcome email to new user"""
        html = EmailTemplate.WELCOME.format(
            name=name,
            dashboard_url=f"{self.base_url}/dashboard",
            docs_url=f"{self.base_url}/docs",
            discord_url=f"{self.base_url}/discord",
            year=self.year
        )
        
        subject = "🎉 Welcome to QA-FRAMEWORK!"
        
        return await self.send_email(to_email, subject, html)

    async def send_waitlist_approved(
        self,
        to_email: str,
        name: str
    ) -> bool:
        """Send waitlist approval email with beta access"""
        html = EmailTemplate.WAITLIST_APPROVED.format(
            name=name,
            email=to_email,
            dashboard_url=f"{self.base_url}/login",
            discord_url=f"{self.base_url}/discord",
            year=self.year
        )

        subject = "🎉 You're Approved! Welcome to QA-FRAMEWORK Beta"

        return await self.send_email(to_email, subject, html)

    async def send_test_report(
        self,
        to_email: str,
        project_name: str,
        execution_date: str,
        total_tests: int,
        passed: int,
        failed: int,
        duration: str,
        report_url: str,
        failed_tests: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Send test execution report"""
        success_rate = round((passed / total_tests * 100) if total_tests > 0 else 0, 1)
        
        # Determine colors and emoji based on success rate
        if success_rate >= 90:
            header_color = "#4CAF50"
            accent_color = "#4CAF50"
            status_emoji = "✅"
        elif success_rate >= 70:
            header_color = "#ff9800"
            accent_color = "#ff9800"
            status_emoji = "⚠️"
        else:
            header_color = "#f44336"
            accent_color = "#f44336"
            status_emoji = "❌"
        
        # Build failed tests section
        failed_tests_section = ""
        if failed_tests and len(failed_tests) > 0:
            failed_tests_section = "<h3>Failed Tests:</h3><ul>"
            for test in failed_tests[:5]:  # Show max 5 failed tests
                failed_tests_section += f"<li><strong>{test['name']}</strong>: {test.get('error', 'Unknown error')}</li>"
            if len(failed_tests) > 5:
                failed_tests_section += f"<li><em>...and {len(failed_tests) - 5} more</em></li>"
            failed_tests_section += "</ul>"
        
        html = EmailTemplate.TEST_REPORT.format(
            project_name=project_name,
            execution_date=execution_date,
            total_tests=total_tests,
            passed=passed,
            failed=failed,
            duration=duration,
            success_rate=success_rate,
            report_url=report_url,
            failed_tests_section=failed_tests_section,
            header_color=header_color,
            accent_color=accent_color,
            status_emoji=status_emoji,
            settings_url=f"{self.base_url}/settings/notifications",
            year=self.year
        )
        
        subject = f"{status_emoji} Test Report: {project_name} - {success_rate}% passed"
        
        return await self.send_email(to_email, subject, html)
    
    async def send_password_reset(
        self,
        to_email: str,
        name: str,
        reset_token: str,
        expires_in: int = 24
    ) -> bool:
        """Send password reset email"""
        reset_url = f"{self.base_url}/reset-password?token={reset_token}"
        
        html = EmailTemplate.PASSWORD_RESET.format(
            name=name,
            reset_url=reset_url,
            expires_in=expires_in,
            year=self.year
        )
        
        subject = "🔐 Reset Your QA-FRAMEWORK Password"
        
        return await self.send_email(to_email, subject, html)


# Create singleton instance
email_service = EmailService()


# Export functions
async def send_beta_invitation(to_email: str, name: str, referral_code: str, accept_url: Optional[str] = None) -> bool:
    """Send beta tester invitation"""
    return await email_service.send_beta_invitation(to_email, name, referral_code, accept_url)


async def send_welcome_email(to_email: str, name: str) -> bool:
    """Send welcome email"""
    return await email_service.send_welcome_email(to_email, name)


async def send_test_report(
    to_email: str,
    project_name: str,
    execution_date: str,
    total_tests: int,
    passed: int,
    failed: int,
    duration: str,
    report_url: str,
    failed_tests: Optional[List[Dict[str, Any]]] = None
) -> bool:
    """Send test execution report"""
    return await email_service.send_test_report(
        to_email, project_name, execution_date, total_tests, passed, failed, duration, report_url, failed_tests
    )


async def send_password_reset(to_email: str, name: str, reset_token: str, expires_in: int = 24) -> bool:
    """Send password reset email"""
    return await email_service.send_password_reset(to_email, name, reset_token, expires_in)
