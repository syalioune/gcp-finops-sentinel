#!/usr/bin/env python3
"""
Test script for sending sample emails to MailHog for template visualization.

This script sends sample budget alert and policy action emails to MailHog
so you can preview the email templates in your browser.

Usage:
    # With Docker Compose (MailHog at mailhog:1025)
    docker compose exec budget-function python /workspace/../scripts/test-email-templates.py

    # Local testing (MailHog at localhost:1025)
    export SMTP_HOST=localhost
    export SMTP_PORT=1025
    python scripts/test-email-templates.py

View emails at: http://localhost:8025
"""

import os
import sys
import time
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from email_service import EmailService


def send_budget_alert_samples():
    """Send sample budget alert emails with different thresholds."""
    print("=" * 60)
    print("Sending Budget Alert Email Samples")
    print("=" * 60)

    # Initialize email service
    smtp_host = os.environ.get("SMTP_HOST", "localhost")
    smtp_port = int(os.environ.get("SMTP_PORT", "1025"))
    template_dir = os.environ.get("TEMPLATE_DIR")

    email_service = EmailService(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_use_tls=False,  # MailHog doesn't use TLS
        from_email="finops-sentinel@example.com",
        template_dir=template_dir,
    )

    # Sample 1: Warning threshold (80%)
    print("\n1. Sending WARNING budget alert (80% threshold)...")
    budget_data_warning = {
        "cost_amount": 800.00,
        "budget_amount": 1000.00,
        "threshold_percent": 80.0,
        "billing_account_id": "012345-ABCDEF-123456",
        "budget_id": "monthly-budget-2025-01",
        "organization_id": "123456789012",
    }

    success = email_service.send_budget_alert_email(
        to_emails=["finops-team@example.com", "admin@example.com"],
        budget_data=budget_data_warning,
        custom_message="Your budget is approaching the warning threshold. Please review your spending.",
    )
    print(f"   Result: {'✓ SUCCESS' if success else '✗ FAILED'}")

    # Sample 2: High threshold (95%)
    print("\n2. Sending HIGH budget alert (95% threshold)...")
    budget_data_high = {
        "cost_amount": 950.00,
        "budget_amount": 1000.00,
        "threshold_percent": 95.0,
        "billing_account_id": "012345-ABCDEF-123456",
        "budget_id": "monthly-budget-2025-01",
        "organization_id": "123456789012",
    }

    actions_high = [
        {
            "type": "log_only",
            "resource_id": "dev-project-1",
            "resource_type": "project",
            "details": "Warning logged for budget threshold",
        }
    ]

    success = email_service.send_budget_alert_email(
        to_emails=["finops-team@example.com"],
        budget_data=budget_data_high,
        actions=actions_high,
        custom_message="Budget is at 95%. Consider immediate cost optimization.",
    )
    print(f"   Result: {'✓ SUCCESS' if success else '✗ FAILED'}")

    # Sample 3: Critical threshold (120%)
    print("\n3. Sending CRITICAL budget alert (120% threshold with actions)...")
    budget_data_critical = {
        "cost_amount": 1200.00,
        "budget_amount": 1000.00,
        "threshold_percent": 120.0,
        "billing_account_id": "012345-ABCDEF-123456",
        "budget_id": "monthly-budget-2025-01",
        "organization_id": "123456789012",
    }

    actions_critical = [
        {
            "type": "restrict_services",
            "resource_id": "production-project-1",
            "resource_type": "project",
            "details": "Restricted services: compute.googleapis.com, container.googleapis.com",
        },
        {
            "type": "restrict_services",
            "resource_id": "production-project-2",
            "resource_type": "project",
            "details": "Restricted services: compute.googleapis.com",
        },
        {
            "type": "apply_constraint",
            "resource_id": "production-project-1",
            "resource_type": "project",
            "details": "Applied constraint: compute.vmExternalIpAccess (enforce=True)",
        },
        {
            "type": "log_only",
            "resource_id": "production-project-1",
            "resource_type": "project",
            "details": "Critical budget threshold - emergency controls activated",
        },
    ]

    success = email_service.send_budget_alert_email(
        to_emails=["finops-team@example.com", "sre-team@example.com", "cfo@example.com"],
        budget_data=budget_data_critical,
        actions=actions_critical,
        custom_message="CRITICAL: Budget exceeded by 20%. Automated cost controls have been activated to prevent further overspend. Compute services have been restricted on production projects.",
    )
    print(f"   Result: {'✓ SUCCESS' if success else '✗ FAILED'}")


def send_policy_action_samples():
    """Send sample policy action event emails."""
    print("\n" + "=" * 60)
    print("Sending Policy Action Event Email Samples")
    print("=" * 60)

    # Initialize email service
    smtp_host = os.environ.get("SMTP_HOST", "localhost")
    smtp_port = int(os.environ.get("SMTP_PORT", "1025"))
    template_dir = os.environ.get("TEMPLATE_DIR")

    email_service = EmailService(
        smtp_host=smtp_host,
        smtp_port=smtp_port,
        smtp_use_tls=False,  # MailHog doesn't use TLS
        from_email="finops-sentinel@example.com",
        template_dir=template_dir,
    )

    # Sample 1: Successful service restriction
    print("\n1. Sending SUCCESSFUL policy action (restrict_services)...")
    action_event_success = {
        "timestamp": time.time(),
        "action_type": "restrict_services",
        "resource_type": "project",
        "resource_id": "production-project-123",
        "organization_id": "123456789012",
        "success": True,
        "details": {
            "constraint": "gcp.restrictServiceUsage",
            "action": "deny",
            "services": [
                "compute.googleapis.com",
                "container.googleapis.com",
                "aiplatform.googleapis.com",
            ],
        },
    }

    success = email_service.send_policy_action_email(
        to_emails=["sre-team@example.com", "finops-team@example.com"],
        action_event=action_event_success,
    )
    print(f"   Result: {'✓ SUCCESS' if success else '✗ FAILED'}")

    # Sample 2: Successful constraint application
    print("\n2. Sending SUCCESSFUL policy action (apply_constraint)...")
    action_event_constraint = {
        "timestamp": time.time(),
        "action_type": "apply_constraint",
        "resource_type": "folder",
        "resource_id": "987654321",
        "organization_id": "123456789012",
        "success": True,
        "details": {
            "constraint": "compute.vmExternalIpAccess",
            "enforce": True,
            "values": None,
        },
    }

    success = email_service.send_policy_action_email(
        to_emails=["sre-team@example.com"],
        action_event=action_event_constraint,
    )
    print(f"   Result: {'✓ SUCCESS' if success else '✗ FAILED'}")

    # Sample 3: Failed policy action
    print("\n3. Sending FAILED policy action (with error details)...")
    action_event_failed = {
        "timestamp": time.time(),
        "action_type": "apply_constraint",
        "resource_type": "project",
        "resource_id": "dev-project-456",
        "organization_id": "123456789012",
        "success": False,
        "details": {
            "constraint": "compute.requireShieldedVm",
            "enforce": True,
            "values": None,
            "error": "Permission denied: The caller does not have permission to access the resource. "
            "Required IAM permission: orgpolicy.policy.set on organization 123456789012.",
        },
    }

    success = email_service.send_policy_action_email(
        to_emails=["sre-team@example.com", "platform-team@example.com"],
        action_event=action_event_failed,
    )
    print(f"   Result: {'✓ SUCCESS' if success else '✗ FAILED'}")


def main():
    """Main function to send all sample emails."""
    print("\n" + "=" * 60)
    print("Email Template Testing Script")
    print("=" * 60)
    print(f"SMTP Host: {os.environ.get('SMTP_HOST', 'localhost')}")
    print(f"SMTP Port: {os.environ.get('SMTP_PORT', '1025')}")
    print(f"Template Dir: {os.environ.get('TEMPLATE_DIR', 'built-in templates')}")
    print(f"View emails at: http://localhost:8025")
    print("=" * 60)

    try:
        # Send budget alert samples
        send_budget_alert_samples()

        # Send policy action samples
        send_policy_action_samples()

        print("\n" + "=" * 60)
        print("✓ All sample emails sent successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Open http://localhost:8025 in your browser")
        print("2. Review the email templates")
        print("3. Check formatting, colors, and content")
        print("4. Customize templates in email-templates/ directory")
        print("5. Re-run this script to see your changes")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\n✗ Error sending emails: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
