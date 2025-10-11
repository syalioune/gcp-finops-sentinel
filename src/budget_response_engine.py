"""
Budget Response Engine - Applies policy actions on GCP projects.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional

from google.api_core.exceptions import NotFound
from google.cloud.orgpolicy_v2 import OrgPolicyClient
from google.cloud.orgpolicy_v2.types import Policy, PolicySpec
from google.cloud.pubsub_v1 import PublisherClient

from email_service import EmailService

logger = logging.getLogger(__name__)


class BudgetResponseEngine:
    """Engine for processing budget alerts and applying policy responses."""

    def __init__(
        self,
        organization_id: str,
        event_topic: Optional[str] = None,
        dry_run: bool = False,
        email_service: Optional[EmailService] = None,
    ):
        """
        Initialize the budget response engine.

        Args:
            organization_id: GCP Organization ID
            event_topic: Optional Pub/Sub topic for publishing action events
                        Format: projects/{project_id}/topics/{topic_id}
            dry_run: If True, log actions without executing them (for testing)
            email_service: Optional EmailService instance for sending emails
        """
        self.organization_id = organization_id
        self.event_topic = event_topic
        self.dry_run = dry_run

        if self.dry_run:
            logger.info("DRY-RUN MODE: Actions will be logged but not executed")
            self.org_policy_client = None
        else:
            self.org_policy_client = OrgPolicyClient()
            logger.info("Initialized with real OrgPolicyClient")

        # Initialize Pub/Sub publisher if topic is configured
        if self.event_topic:
            self.publisher = PublisherClient()
            logger.info("Initialized PublisherClient for action events")
        else:
            self.publisher = None
            logger.info("Event publishing disabled (no topic configured)")

        # Initialize email service if provided or create default
        # NOTE: Email service is independent of BudgetResponseEngine dry_run
        # Email sending is controlled by SMTP configuration only
        if email_service:
            self.email_service = email_service
        else:
            # Try to initialize with environment variables
            # EmailService will raise ValueError if SMTP is not configured
            try:
                self.email_service = EmailService()
                logger.info("Email service initialized successfully")
            except ValueError as e:
                # SMTP not configured, email service disabled
                self.email_service = None
                logger.info("Email service disabled: %s", str(e))

    def get_resource_parent(self, resource_id: str, resource_type: str = "project") -> str:
        """
        Get the resource name for org policy operations.

        Args:
            resource_id: Resource ID (project ID, folder ID, or organization ID)
            resource_type: Type of resource ('project', 'folder', or 'organization')

        Returns:
            str: Formatted resource name
        """
        if resource_type == "project":
            return f"projects/{resource_id}"
        elif resource_type == "folder":
            return f"folders/{resource_id}"
        elif resource_type == "organization":
            return f"organizations/{resource_id}"
        else:
            raise ValueError(f"Invalid resource_type: {resource_type}")

    def upsert_policy(self, policy: Policy) -> None:
        """
        Create or update a policy (upsert logic).

        Args:
            policy: Policy object to create or update

        Raises:
            Exception: If the operation fails for reasons other than 404
        """
        try:
            # Try to get the existing policy first
            self.org_policy_client.get_policy(name=policy.name)
            # If it exists, update it
            self.org_policy_client.update_policy(policy=policy)
            logger.debug("Updated existing policy: %s", policy.name)
        except NotFound:
            # Policy doesn't exist, create it
            # Extract parent from policy name (format: projects/123/policies/constraint)
            parent = "/".join(policy.name.split("/")[:-2])
            self.org_policy_client.create_policy(parent=parent, policy=policy)
            logger.debug("Created new policy: %s", policy.name)
        except Exception:
            # Re-raise other exceptions
            raise

    def publish_action_event(
        self,
        action_type: str,
        resource_id: str,
        resource_type: str,
        success: bool,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Publish an action event to the configured Pub/Sub topic.

        Args:
            action_type: Type of action executed (e.g., 'restrict_services')
            resource_id: GCP Resource ID where action was applied
            resource_type: Type of resource ('project', 'folder', or 'organization')
            success: Whether the action was successful
            details: Additional action-specific details
        """
        if not self.publisher or not self.event_topic:
            return

        try:

            event_data = {
                "timestamp": time.time(),
                "action_type": action_type,
                "resource_id": resource_id,
                "resource_type": resource_type,
                "success": success,
                "organization_id": self.organization_id,
                "details": details or {},
            }

            message_data = json.dumps(event_data).encode("utf-8")
            future = self.publisher.publish(self.event_topic, message_data)

            # For mock publisher, result is immediate. For real, this blocks briefly
            message_id = future.result(timeout=5.0)

            logger.info(
                "Published action event to %s: %s on %s/%s (message_id: %s)",
                self.event_topic,
                action_type,
                resource_type,
                resource_id,
                message_id,
            )

        except Exception as e:
            # Don't fail the main flow if event publishing fails
            logger.error("Failed to publish action event: %s", e, exc_info=True)

    def apply_service_restriction(
        self,
        resource_id: str,
        services: List[str],
        action: str = "deny",
        resource_type: str = "project",
    ) -> bool:
        """
        Apply service restriction policy to a resource (project, folder, or organization).

        Args:
            resource_id: GCP Resource ID (project ID, folder ID, or organization ID)
            services: List of service names to restrict (e.g., 'compute.googleapis.com')
            action: 'deny' to disable services, 'allow' to enable services
            resource_type: Type of resource ('project', 'folder', or 'organization')

        Returns:
            bool: True if successful, False otherwise
        """
        success = False
        error_message = None
        constraint = "gcp.restrictServiceUsage"

        try:
            if self.dry_run:
                logger.info(
                    "DRY-RUN: Would apply service restriction to %s %s: " "%s %s (constraint: %s)",
                    resource_type,
                    resource_id,
                    action,
                    services,
                    constraint,
                )
                success = True
            else:
                parent = self.get_resource_parent(resource_id, resource_type)

                # Build the policy rule
                policy_rule = PolicySpec.PolicyRule()

                if action == "deny":
                    policy_rule.values = PolicySpec.PolicyRule.StringValues(denied_values=services)
                else:
                    policy_rule.values = PolicySpec.PolicyRule.StringValues(allowed_values=services)

                # Build the policy
                policy = Policy(
                    name=f"{parent}/policies/{constraint}",
                    spec=PolicySpec(rules=[policy_rule], inherit_from_parent=True),
                )

                # Apply the policy (create or update)
                self.upsert_policy(policy=policy)
                logger.info(
                    "Applied service restriction to %s %s: " "%s %s",
                    resource_type,
                    resource_id,
                    action,
                    services,
                )
                success = True

        except Exception as e:
            error_message = str(e)
            logger.error(
                "Failed to apply service restriction to %s %s: %s", resource_type, resource_id, e
            )

        # Publish action event
        self.publish_action_event(
            action_type="restrict_services",
            resource_id=resource_id,
            resource_type=resource_type,
            success=success,
            details={
                "constraint": constraint,
                "action": action,
                "services": services,
                "error": error_message,
            },
        )

        return success

    def apply_custom_constraint(
        self,
        resource_id: str,
        constraint: str,
        enforce: bool = True,
        values: Optional[List[str]] = None,
        resource_type: str = "project",
    ) -> bool:
        """
        Apply a custom organization policy constraint.

        Args:
            resource_id: GCP Resource ID (project ID, folder ID, or organization ID)
            constraint: Constraint name (e.g., 'compute.vmExternalIpAccess')
            enforce: Whether to enforce the constraint
            values: Optional list of values for list constraints
            resource_type: Type of resource ('project', 'folder', or 'organization')

        Returns:
            bool: True if successful, False otherwise
        """
        success = False
        error_message = None

        try:
            if self.dry_run:
                logger.info(
                    "DRY-RUN: Would apply constraint %s to %s %s: " "enforce=%s, values=%s",
                    constraint,
                    resource_type,
                    resource_id,
                    enforce,
                    values,
                )
                success = True
            else:
                parent = self.get_resource_parent(resource_id, resource_type)

                # Build the policy rule
                policy_rule = PolicySpec.PolicyRule()

                if values:
                    # List constraint - deny specific values
                    policy_rule.values = PolicySpec.PolicyRule.StringValues(denied_values=values)
                else:
                    # Boolean constraint
                    policy_rule.enforce = enforce

                # Build the policy
                policy = Policy(
                    name=f"{parent}/policies/{constraint}",
                    spec=PolicySpec(rules=[policy_rule]),
                )

                # Apply the policy (create or update)
                self.upsert_policy(policy=policy)

                logger.info(
                    "Applied constraint %s to %s %s: " "enforce=%s, values=%s",
                    constraint,
                    resource_type,
                    resource_id,
                    enforce,
                    values,
                )
                success = True

        except Exception as e:
            error_message = str(e)
            logger.error(
                "Failed to apply constraint %s to %s %s: %s",
                constraint,
                resource_type,
                resource_id,
                e,
            )

        # Publish action event
        self.publish_action_event(
            action_type="apply_constraint",
            resource_id=resource_id,
            resource_type=resource_type,
            success=success,
            details={
                "constraint": constraint,
                "enforce": enforce,
                "values": values,
                "error": error_message,
            },
        )

        return success

    def send_email(
        self,
        to_emails: List[str],
        template: str = "budget_alert",
        budget_data: Optional[Dict[str, Any]] = None,
        action_event: Optional[Dict[str, Any]] = None,
        custom_message: Optional[str] = None,
        actions_taken: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """
        Send an email notification using configured EmailService.

        Args:
            to_emails: List of recipient email addresses
            template: Template to use ('budget_alert' or 'policy_action')
            budget_data: Budget alert data (for budget_alert template)
            action_event: Policy action event data (for policy_action template)
            custom_message: Custom message to include
            actions_taken: List of actions that were executed (for budget_alert template)

        Returns:
            bool: True if sent successfully, False otherwise
        """
        success = False
        error_message = None

        try:
            if not self.email_service:
                error_message = "SMTP not configured - email service unavailable"
                logger.warning(error_message)
                # Note: We still publish the action event below to record the attempt
                success = False
            elif template == "budget_alert":
                if not budget_data:
                    logger.error("budget_data required for budget_alert template")
                    return False

                # Add organization_id to context
                budget_data_with_org = {
                    **budget_data,
                    "organization_id": self.organization_id,
                }

                success = self.email_service.send_budget_alert_email(
                    to_emails=to_emails,
                    budget_data=budget_data_with_org,
                    actions=actions_taken,
                    custom_message=custom_message,
                )

            elif template == "policy_action":
                if not action_event:
                    logger.error("action_event required for policy_action template")
                    return False

                success = self.email_service.send_policy_action_email(
                    to_emails=to_emails,
                    action_event=action_event,
                )

            else:
                logger.error("Unknown email template: %s", template)
                return False

            if success:
                logger.info(
                    "Email sent successfully using template '%s' to %s",
                    template,
                    ", ".join(to_emails),
                )

        except Exception as e:
            error_message = str(e)
            logger.error("Failed to send email: %s", e, exc_info=True)

        # Publish action event for email sending
        self.publish_action_event(
            action_type="send_email",
            resource_id="email",
            resource_type="notification",
            success=success,
            details={
                "template": template,
                "recipients": to_emails,
                "error": error_message,
            },
        )

        return success
