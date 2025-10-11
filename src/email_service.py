"""
Email Service - Sends HTML emails via SMTP with Jinja2 templating.
"""

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional

from jinja2 import Environment, FileSystemLoader, Template

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending templated HTML emails via SMTP."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        smtp_use_tls: Optional[bool] = None,
        from_email: Optional[str] = None,
        template_dir: Optional[str] = None,
    ):
        """
        Initialize the email service.

        Args:
            smtp_host: SMTP server hostname (required)
            smtp_port: SMTP server port (default: 587 for TLS, 25 for non-TLS)
            smtp_user: SMTP authentication username
            smtp_password: SMTP authentication password
            smtp_use_tls: Whether to use TLS encryption (default: True)
            from_email: Default sender email address (required)
            template_dir: Directory containing Jinja2 email templates
        """
        # Load from environment if not provided
        self.smtp_host = smtp_host or os.environ.get("SMTP_HOST")

        # Read SMTP_USE_TLS from environment variable if not provided
        if smtp_use_tls is None:
            smtp_use_tls_env = os.environ.get("SMTP_USE_TLS", "true").lower()
            self.smtp_use_tls = smtp_use_tls_env in ("true", "1", "yes")
        else:
            self.smtp_use_tls = smtp_use_tls

        self.smtp_port = smtp_port or int(
            os.environ.get("SMTP_PORT", "587" if self.smtp_use_tls else "25")
        )
        self.smtp_user = smtp_user or os.environ.get("SMTP_USER")
        self.smtp_password = smtp_password or os.environ.get("SMTP_PASSWORD")
        self.from_email = from_email or os.environ.get("SMTP_FROM_EMAIL", self.smtp_user)

        # Validate required configuration - SMTP must be fully configured
        if not self.smtp_host:
            raise ValueError("SMTP_HOST is required for email service")
        if not self.from_email:
            raise ValueError("SMTP_FROM_EMAIL is required for email service")

        # Setup Jinja2 template environment
        # Check for template directory from parameter, environment, or use default
        template_directory = template_dir or os.environ.get("TEMPLATE_DIR")

        # Default to ../email-templates relative to this file if not specified
        if not template_directory:
            # Get the directory containing this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up one level and into email-templates
            default_template_dir = os.path.join(os.path.dirname(current_dir), "email-templates")
            if os.path.isdir(default_template_dir):
                template_directory = default_template_dir
                logger.info("Using default template directory: %s", template_directory)

        if template_directory and os.path.isdir(template_directory):
            self.template_env = Environment(
                loader=FileSystemLoader(template_directory),
                autoescape=True,
            )
            logger.info("Email templates loaded from: %s", template_directory)
        else:
            error_msg = (
                f"Template directory not found: {template_directory or 'no directory specified'}"
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(
            "EmailService initialized: %s:%s (TLS: %s)",
            self.smtp_host,
            self.smtp_port,
            self.smtp_use_tls,
        )

    def render_template(self, template_name: str, context: Dict[str, Any]) -> tuple[str, str]:
        """
        Render email template with given context.

        Args:
            template_name: Template name ('budget_alert' or 'policy_action') or custom
            context: Template context variables

        Returns:
            tuple: (subject, html_body)
        """
        try:
            # Load template from configured directory
            template = self.template_env.get_template(f"{template_name}.html")
            subject_template_obj = self.template_env.get_template(f"{template_name}_subject.txt")
            subject = subject_template_obj.render(context).strip()
            html_body = template.render(context)
            return subject, html_body
        except Exception as e:
            logger.error("Failed to load template '%s': %s", template_name, e, exc_info=True)
            raise ValueError(f"Template '{template_name}' not found or failed to render: {e}")

    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        html_body: str,
        from_email: Optional[str] = None,
    ) -> bool:
        """
        Send an HTML email via SMTP.

        Args:
            to_emails: List of recipient email addresses
            subject: Email subject line
            html_body: HTML email body
            from_email: Sender email (defaults to configured from_email)

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not to_emails:
            logger.warning("No recipient emails provided")
            return False

        sender = from_email or self.from_email

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = sender
            msg["To"] = ", ".join(to_emails)

            # Attach HTML body
            html_part = MIMEText(html_body, "html")
            msg.attach(html_part)

            # Send via SMTP
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls()

                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)

                server.send_message(msg)

            logger.info("Email sent successfully to %s: %s", ", ".join(to_emails), subject)
            return True

        except Exception as e:
            logger.error("Failed to send email: %s", e, exc_info=True)
            return False

    def send_budget_alert_email(
        self,
        to_emails: List[str],
        budget_data: Dict[str, Any],
        actions: Optional[List[Dict[str, Any]]] = None,
        custom_message: Optional[str] = None,
    ) -> bool:
        """
        Send a budget alert notification email.

        Args:
            to_emails: List of recipient email addresses
            budget_data: Budget alert data including cost, budget, threshold
            actions: List of automated actions taken (optional)
            custom_message: Custom message to include in email (optional)

        Returns:
            bool: True if sent successfully, False otherwise
        """
        context = {
            **budget_data,
            "actions": actions or [],
            "custom_message": custom_message,
        }

        subject, html_body = self.render_template("budget_alert", context)
        return self.send_email(to_emails, subject, html_body)

    def send_policy_action_email(
        self,
        to_emails: List[str],
        action_event: Dict[str, Any],
    ) -> bool:
        """
        Send a policy action event notification email.

        Args:
            to_emails: List of recipient email addresses
            action_event: Policy action event data

        Returns:
            bool: True if sent successfully, False otherwise
        """
        # Format timestamp for readability
        from datetime import datetime

        if "timestamp" in action_event:
            dt = datetime.fromtimestamp(action_event["timestamp"])
            action_event["timestamp"] = dt.strftime("%Y-%m-%d %H:%M:%S UTC")

        subject, html_body = self.render_template("policy_action", action_event)
        return self.send_email(to_emails, subject, html_body)
