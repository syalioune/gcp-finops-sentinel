"""
Unit tests for EmailService.
"""

import os
from unittest.mock import MagicMock, patch

import pytest

from email_service import EmailService


class TestEmailServiceInit:
    """Tests for EmailService initialization."""

    def test_init_with_params(self):
        """Test initialization with explicit parameters."""
        service = EmailService(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_password="secret",  # pragma: allowlist secret
            from_email="sender@example.com",
        )

        assert service.smtp_host == "smtp.example.com"
        assert service.smtp_port == 587
        assert service.smtp_user == "user@example.com"
        assert service.smtp_password == "secret"  # pragma: allowlist secret
        assert service.from_email == "sender@example.com"
        assert service.smtp_use_tls is True  # Default is True when not specified

    def test_init_with_env_vars(self):
        """Test initialization from environment variables."""
        env = {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_PORT": "465",
            "SMTP_USER": "test@test.com",
            "SMTP_PASSWORD": "pass123",  # pragma: allowlist secret
            "SMTP_FROM_EMAIL": "noreply@test.com",
        }

        with patch.dict(os.environ, env):
            service = EmailService()

        assert service.smtp_host == "smtp.test.com"
        assert service.smtp_port == 465
        assert service.smtp_user == "test@test.com"
        assert service.from_email == "noreply@test.com"

    def test_init_with_tls_env_var_true(self):
        """Test initialization with SMTP_USE_TLS=true from environment."""
        env = {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_USE_TLS": "true",
            "SMTP_FROM_EMAIL": "test@test.com",
        }

        with patch.dict(os.environ, env):
            service = EmailService()

        assert service.smtp_use_tls is True
        assert service.smtp_port == 587  # Default TLS port

    def test_init_with_tls_env_var_false(self):
        """Test initialization with SMTP_USE_TLS=false from environment."""
        env = {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_USE_TLS": "false",
            "SMTP_FROM_EMAIL": "test@test.com",
        }

        with patch.dict(os.environ, env):
            service = EmailService()

        assert service.smtp_use_tls is False
        assert service.smtp_port == 25  # Default non-TLS port

    def test_init_with_tls_env_var_1(self):
        """Test initialization with SMTP_USE_TLS=1 from environment."""
        env = {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_USE_TLS": "1",
            "SMTP_FROM_EMAIL": "test@test.com",
        }

        with patch.dict(os.environ, env):
            service = EmailService()

        assert service.smtp_use_tls is True

    def test_init_with_tls_env_var_yes(self):
        """Test initialization with SMTP_USE_TLS=yes from environment."""
        env = {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_USE_TLS": "yes",
            "SMTP_FROM_EMAIL": "test@test.com",
        }

        with patch.dict(os.environ, env):
            service = EmailService()

        assert service.smtp_use_tls is True

    def test_init_with_tls_default(self):
        """Test initialization with default TLS setting (true)."""
        env = {
            "SMTP_HOST": "smtp.test.com",
            "SMTP_FROM_EMAIL": "test@test.com",
        }

        with patch.dict(os.environ, env, clear=True):
            service = EmailService()

        assert service.smtp_use_tls is True  # Default is True

    def test_init_missing_smtp_host_raises(self):
        """Test that missing SMTP host raises ValueError."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="SMTP_HOST is required"):
                EmailService()

    def test_init_missing_from_email_raises(self):
        """Test that missing from_email raises ValueError."""
        with patch.dict(os.environ, {"SMTP_HOST": "smtp.test.com"}, clear=True):
            with pytest.raises(ValueError, match="SMTP_FROM_EMAIL is required"):
                EmailService()

    def test_init_tls_disabled(self):
        """Test initialization with TLS disabled."""
        service = EmailService(
            smtp_host="smtp.example.com",
            smtp_use_tls=False,
            from_email="test@test.com",
        )

        assert service.smtp_use_tls is False
        assert service.smtp_port == 25  # Default port for non-TLS


class TestEmailTemplates:
    """Tests for email template rendering."""

    def test_render_budget_alert_template(self):
        """Test rendering budget alert template."""
        service = EmailService(smtp_host="smtp.test.com", from_email="test@test.com")

        context = {
            "cost_amount": 1500.0,
            "budget_amount": 1000.0,
            "threshold_percent": 150.0,
            "billing_account_id": "012345-ABCDEF-123456",
            "budget_id": "budget-123",
            "organization_id": "123456789012",
            "actions": [],
            "custom_message": None,
        }

        subject, html_body = service.render_template("budget_alert", context)

        # Subject line format from external template
        assert "150.0%" in subject
        assert "Budget Alert" in subject
        assert "€1500.00" in html_body
        assert "€1000.00" in html_body
        assert "150.0%" in html_body
        assert "012345-ABCDEF-123456" in html_body

    def test_render_budget_alert_with_actions(self):
        """Test rendering budget alert template with actions list."""
        service = EmailService(smtp_host="smtp.test.com", from_email="test@test.com")

        context = {
            "cost_amount": 950.0,
            "budget_amount": 1000.0,
            "threshold_percent": 95.0,
            "billing_account_id": "012345-ABCDEF-123456",
            "budget_id": "budget-123",
            "organization_id": "123456789012",
            "actions": [
                {
                    "type": "restrict_services",
                    "resource_id": "my-project",
                    "resource_type": "project",
                    "details": "Restricted compute.googleapis.com",
                },
            ],
            "custom_message": "Critical budget threshold exceeded!",
        }

        subject, html_body = service.render_template("budget_alert", context)

        assert "restrict_services" in html_body
        assert "my-project" in html_body
        assert "Critical budget threshold exceeded!" in html_body

    def test_render_policy_action_template(self):
        """Test rendering policy action template."""
        service = EmailService(smtp_host="smtp.test.com", from_email="test@test.com")

        context = {
            "timestamp": "2025-01-20 10:30:00 UTC",
            "action_type": "restrict_services",
            "resource_type": "project",
            "resource_id": "my-project-123",
            "organization_id": "123456789012",
            "success": True,
            "details": {
                "constraint": "gcp.restrictServiceUsage",
                "services": ["compute.googleapis.com"],
            },
        }

        subject, html_body = service.render_template("policy_action", context)

        assert "restrict_services" in subject
        assert "my-project-123" in subject
        assert "restrict_services" in html_body
        assert "my-project-123" in html_body
        assert "Success" in html_body

    def test_render_policy_action_with_error(self):
        """Test rendering policy action template with error."""
        service = EmailService(smtp_host="smtp.test.com", from_email="test@test.com")

        context = {
            "timestamp": "2025-01-20 10:30:00 UTC",
            "action_type": "apply_constraint",
            "resource_type": "project",
            "resource_id": "my-project-456",
            "organization_id": "123456789012",
            "success": False,
            "details": {
                "constraint": "compute.vmExternalIpAccess",
                "error": "Permission denied: Insufficient IAM permissions",
            },
        }

        subject, html_body = service.render_template("policy_action", context)

        assert "Failed" in html_body
        assert "Permission denied" in html_body

    def test_render_unknown_template_raises(self):
        """Test that unknown template raises ValueError."""
        service = EmailService(smtp_host="smtp.test.com", from_email="test@test.com")

        with pytest.raises(ValueError, match="Template .* not found"):
            service.render_template("unknown_template", {})


class TestEmailSending:
    """Tests for email sending functionality."""

    @patch("email_service.smtplib.SMTP")
    def test_send_email_success_with_tls(self, mock_smtp_class):
        """Test successful email sending with TLS."""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        service = EmailService(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_user="user@example.com",
            smtp_password="secret",  # pragma: allowlist secret
            smtp_use_tls=True,
            from_email="sender@example.com",
        )

        result = service.send_email(
            to_emails=["recipient@example.com"],
            subject="Test Subject",
            html_body="<html><body>Test</body></html>",
        )

        assert result is True
        mock_smtp_class.assert_called_once_with("smtp.example.com", 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with("user@example.com", "secret")
        mock_server.send_message.assert_called_once()

    @patch("email_service.smtplib.SMTP")
    def test_send_email_success_no_auth(self, mock_smtp_class):
        """Test successful email sending without authentication."""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        service = EmailService(
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_use_tls=False,
            from_email="sender@example.com",
        )

        result = service.send_email(
            to_emails=["recipient@example.com"],
            subject="Test Subject",
            html_body="<html><body>Test</body></html>",
        )

        assert result is True
        mock_smtp_class.assert_called_once_with("smtp.example.com", 587)
        mock_server.starttls.assert_not_called()
        mock_server.login.assert_not_called()
        mock_server.send_message.assert_called_once()

    @patch("email_service.smtplib.SMTP")
    def test_send_email_no_tls(self, mock_smtp_class):
        """Test email sending without TLS."""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        service = EmailService(
            smtp_host="smtp.example.com",
            smtp_port=25,
            smtp_use_tls=False,
            from_email="sender@example.com",
        )

        result = service.send_email(
            to_emails=["recipient@example.com"],
            subject="Test Subject",
            html_body="<html><body>Test</body></html>",
        )

        assert result is True
        mock_server.starttls.assert_not_called()
        mock_server.login.assert_not_called()

    @patch("email_service.smtplib.SMTP")
    def test_send_email_failure(self, mock_smtp_class):
        """Test email sending failure."""
        mock_smtp_class.return_value.__enter__.side_effect = Exception("SMTP error")

        service = EmailService(
            smtp_host="smtp.example.com",
            from_email="sender@example.com",
        )

        result = service.send_email(
            to_emails=["recipient@example.com"],
            subject="Test Subject",
            html_body="<html><body>Test</body></html>",
        )

        assert result is False

    def test_send_email_no_recipients(self):
        """Test sending email with no recipients."""
        service = EmailService(smtp_host="smtp.test.com", from_email="test@test.com")

        result = service.send_email(
            to_emails=[],
            subject="Test Subject",
            html_body="<html><body>Test</body></html>",
        )

        assert result is False

    @patch("email_service.smtplib.SMTP")
    def test_send_email_multiple_recipients(self, mock_smtp_class):
        """Test sending email to multiple recipients."""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        service = EmailService(
            smtp_host="smtp.example.com",
            from_email="sender@example.com",
        )

        result = service.send_email(
            to_emails=["user1@example.com", "user2@example.com"],
            subject="Test Subject",
            html_body="<html><body>Test</body></html>",
        )

        assert result is True
        mock_server.send_message.assert_called_once()


class TestConvenienceMethods:
    """Tests for convenience email sending methods."""

    @patch("email_service.smtplib.SMTP")
    def test_send_budget_alert_email(self, mock_smtp_class):
        """Test send_budget_alert_email convenience method."""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        service = EmailService(smtp_host="smtp.test.com", from_email="test@test.com")

        budget_data = {
            "cost_amount": 1200.0,
            "budget_amount": 1000.0,
            "threshold_percent": 120.0,
            "billing_account_id": "012345-ABCDEF-123456",
            "budget_id": "budget-123",
            "organization_id": "123456789012",
        }

        result = service.send_budget_alert_email(
            to_emails=["admin@example.com"],
            budget_data=budget_data,
            custom_message="Please review immediately",
        )

        assert result is True

    @patch("email_service.smtplib.SMTP")
    def test_send_budget_alert_email_with_actions(self, mock_smtp_class):
        """Test send_budget_alert_email with actions list."""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        service = EmailService(smtp_host="smtp.test.com", from_email="test@test.com")

        budget_data = {
            "cost_amount": 1500.0,
            "budget_amount": 1000.0,
            "threshold_percent": 150.0,
            "billing_account_id": "012345-ABCDEF-123456",
            "budget_id": "budget-123",
            "organization_id": "123456789012",
        }

        actions = [
            {"type": "restrict_services", "details": "Restricted compute"},
        ]

        result = service.send_budget_alert_email(
            to_emails=["admin@example.com"],
            budget_data=budget_data,
            actions=actions,
        )

        assert result is True

    @patch("email_service.smtplib.SMTP")
    def test_send_policy_action_email(self, mock_smtp_class):
        """Test send_policy_action_email convenience method."""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        service = EmailService(smtp_host="smtp.test.com", from_email="test@test.com")

        action_event = {
            "timestamp": 1234567890.123,
            "action_type": "restrict_services",
            "resource_type": "project",
            "resource_id": "my-project",
            "organization_id": "123456789012",
            "success": True,
            "details": {
                "constraint": "gcp.restrictServiceUsage",
                "services": ["compute.googleapis.com"],
            },
        }

        result = service.send_policy_action_email(
            to_emails=["admin@example.com"],
            action_event=action_event,
        )

        assert result is True

    @patch("email_service.smtplib.SMTP")
    def test_send_policy_action_email_with_error(self, mock_smtp_class):
        """Test send_policy_action_email with error details."""
        mock_server = MagicMock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server

        service = EmailService(smtp_host="smtp.test.com", from_email="test@test.com")

        action_event = {
            "timestamp": 1234567890.123,
            "action_type": "apply_constraint",
            "resource_type": "project",
            "resource_id": "my-project",
            "organization_id": "123456789012",
            "success": False,
            "details": {
                "constraint": "compute.vmExternalIpAccess",
                "error": "Permission denied",
            },
        }

        result = service.send_policy_action_email(
            to_emails=["admin@example.com"],
            action_event=action_event,
        )

        assert result is True
