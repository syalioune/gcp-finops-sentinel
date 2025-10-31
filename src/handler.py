"""
Cloud Function handler for budget alert events.
"""

import base64
import json
import logging
import os

import functions_framework
from google.cloud.billing.budgets_v1 import BudgetServiceClient
from google.cloud.billing_v1 import CloudBillingClient

from budget_response_engine import BudgetResponseEngine
from config import load_rules_config
from project_discovery import ProjectDiscovery
from rule_engine import RuleEngine

logger = logging.getLogger(__name__)

# Check if we should use dry-run mode for testing
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"


def _get_billing_account_display_name(billing_account_id: str, dry_run: bool = False) -> str:
    """
    Fetch the display name for a billing account.

    Args:
        billing_account_id: Billing account ID
        dry_run: If True, return mock data

    Returns:
        Display name or billing_account_id if not found
    """
    if dry_run:
        return f"Mock Billing Account ({billing_account_id})"

    try:
        client = CloudBillingClient()
        billing_account = client.get_billing_account(name=f"billingAccounts/{billing_account_id}")
        return billing_account.display_name or billing_account_id
    except Exception as e:
        logger.warning("Failed to fetch billing account display name: %s", e)
        return billing_account_id


def _get_budget_display_name(billing_account_id: str, budget_id: str, dry_run: bool = False) -> str:
    """
    Fetch the display name for a budget.

    Args:
        billing_account_id: Billing account ID
        budget_id: Budget ID
        dry_run: If True, return mock data

    Returns:
        Display name or budget_id if not found
    """
    if dry_run:
        return f"Mock Budget ({budget_id})"

    try:
        client = BudgetServiceClient()
        budget_name = f"billingAccounts/{billing_account_id}/budgets/{budget_id}"
        budget = client.get_budget(name=budget_name)
        return budget.display_name or budget_id
    except Exception as e:
        logger.warning("Failed to fetch budget display name: %s", e)
        return budget_id


def _resolve_action_targets(action, project_discovery, organization_id):
    """
    Resolve action targets from various targeting methods.

    Args:
        action: Action dictionary containing targeting specifications
        project_discovery: ProjectDiscovery instance for label-based queries
        organization_id: Organization ID for scoping label searches

    Returns:
        List of (resource_id, resource_type, display_name) tuples
        display_name may be None for explicit targets without resolution
    """
    targets = []

    # Add explicit project targets (no display name resolution for now)
    if "target_projects" in action:
        for project_id in action["target_projects"]:
            targets.append((project_id, "project", None))

    # Add explicit folder targets (no display name resolution for now)
    if "target_folders" in action:
        for folder_id in action["target_folders"]:
            targets.append((folder_id, "folder", None))

    # Add organization target (no display name resolution for now)
    if "target_organization" in action:
        org_id = action["target_organization"]
        targets.append((org_id, "organization", None))

    # Add projects discovered by labels
    if "target_labels" in action:
        label_filters = action["target_labels"]
        discovered_projects = project_discovery.find_projects_by_labels(
            label_filters, organization_id
        )
        for project_info in discovered_projects:
            # project_info is a dict with project_id and display_name
            targets.append(
                (project_info["project_id"], "project", project_info.get("display_name"))
            )

    return targets


@functions_framework.cloud_event
def budget_response_handler(cloud_event):
    """
    Cloud Function entry point for budget alert Pub/Sub events.

    Args:
        cloud_event: CloudEvent object containing Pub/Sub message
    """
    try:
        # Decode Pub/Sub message
        pubsub_message = base64.b64decode(cloud_event.data["message"]["data"])
        budget_data = json.loads(pubsub_message)

        # Extract Pub/Sub message attributes (billingAccountId, budgetId)
        attributes = cloud_event.data["message"].get("attributes", {})

        logger.info("Received budget alert: %s", json.dumps(budget_data, indent=2))
        logger.info("Message attributes: %s", json.dumps(attributes, indent=2))

        # Get organization ID from environment
        organization_id = os.environ.get("ORGANIZATION_ID")
        if not organization_id:
            logger.error("ORGANIZATION_ID environment variable not set")
            return

        # Get optional event topic from environment
        event_topic = os.environ.get("ACTION_EVENT_TOPIC")

        # Load rules configuration
        rules_config = load_rules_config()

        # Initialize engines
        rule_engine = RuleEngine(rules_config)
        response_engine = BudgetResponseEngine(
            organization_id, event_topic=event_topic, dry_run=DRY_RUN
        )
        project_discovery = ProjectDiscovery(dry_run=DRY_RUN)

        # Evaluate rules and get actions
        actions = rule_engine.evaluate(budget_data, attributes)

        if not actions:
            logger.info("No actions triggered by this budget alert")
            return

        logger.info("Executing %s actions", len(actions))

        # Track executed actions for email notifications
        executed_actions = []

        # Execute actions
        for action in actions:
            action_type = action.get("type")

            # Handle send_mail action differently (doesn't need resource targets)
            if action_type == "send_mail":
                to_emails = action.get("to_emails", [])
                template = action.get("template", "budget_alert")
                custom_message = action.get("custom_message")

                if not to_emails:
                    logger.warning("send_mail action missing to_emails - skipping")
                    continue

                # Prepare budget data for email template
                cost_amount = budget_data.get("costAmount", 0)
                budget_amount = budget_data.get("budgetAmount", 0)
                threshold_percent = (cost_amount / budget_amount * 100) if budget_amount > 0 else 0

                # Get human-readable names for billing account and budget
                billing_account_id = attributes.get("billingAccountId", "unknown")
                budget_id = attributes.get("budgetId", "unknown")
                billing_account_name = _get_billing_account_display_name(
                    billing_account_id, DRY_RUN
                )
                budget_name = _get_budget_display_name(billing_account_id, budget_id, DRY_RUN)

                email_budget_data = {
                    "cost_amount": cost_amount,
                    "budget_amount": budget_amount,
                    "threshold_percent": threshold_percent,
                    "billing_account_id": billing_account_id,
                    "billing_account_name": billing_account_name,
                    "budget_id": budget_id,
                    "budget_name": budget_name,
                }

                response_engine.send_email(
                    to_emails=to_emails,
                    template=template,
                    budget_data=email_budget_data,
                    custom_message=custom_message,
                    actions_taken=executed_actions,
                )
                continue

            # Resolve target resources for other actions
            targets = _resolve_action_targets(action, project_discovery, organization_id)

            if not targets:
                logger.warning("Action %s has no resolved targets - skipping", action_type)
                continue

            # Execute action for each target resource
            for resource_id, resource_type, display_name in targets:
                # Format display text for logging and email
                display_text = f"{display_name} ({resource_id})" if display_name else resource_id

                if action_type == "restrict_services":
                    services = action.get("services", [])
                    response_engine.apply_service_restriction(
                        resource_id,
                        services,
                        action="deny",
                        resource_type=resource_type,
                        display_name=display_name,
                    )
                    executed_actions.append(
                        {
                            "type": action_type,
                            "resource_id": resource_id,
                            "resource_type": resource_type,
                            "display_name": display_name,
                            "details": f"Restricted services on {display_text}: {', '.join(services)}",
                        }
                    )

                elif action_type == "apply_constraint":
                    constraint = action.get("constraint")
                    enforce = action.get("enforce", True)
                    values = action.get("values")
                    response_engine.apply_custom_constraint(
                        resource_id,
                        constraint,
                        enforce,
                        values,
                        resource_type=resource_type,
                        display_name=display_name,
                    )
                    executed_actions.append(
                        {
                            "type": action_type,
                            "resource_id": resource_id,
                            "resource_type": resource_type,
                            "display_name": display_name,
                            "details": f"Applied constraint on {display_text}: {constraint}",
                        }
                    )

                elif action_type == "log_only":
                    logger.warning(
                        "Log-only action for %s %s: %s",
                        resource_type,
                        display_text,
                        action.get("message", "Budget threshold exceeded"),
                    )
                    executed_actions.append(
                        {
                            "type": action_type,
                            "resource_id": resource_id,
                            "resource_type": resource_type,
                            "display_name": display_name,
                            "details": action.get("message", "Budget threshold exceeded"),
                        }
                    )

                else:
                    logger.warning("Unknown action type: %s", action_type)

        logger.info("Budget response processing completed")

    except Exception as e:
        logger.error("Error processing budget alert: %s", e, exc_info=True)
        raise
