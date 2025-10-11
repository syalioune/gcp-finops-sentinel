"""
Cloud Function handler for budget alert events.
"""

import base64
import json
import logging
import os

import functions_framework

from budget_response_engine import BudgetResponseEngine
from config import load_rules_config
from project_discovery import ProjectDiscovery
from rule_engine import RuleEngine

logger = logging.getLogger(__name__)

# Check if we should use dry-run mode for testing
DRY_RUN = os.environ.get("DRY_RUN", "false").lower() == "true"


def _resolve_action_targets(action, project_discovery, organization_id):
    """
    Resolve action targets from various targeting methods.

    Args:
        action: Action dictionary containing targeting specifications
        project_discovery: ProjectDiscovery instance for label-based queries
        organization_id: Organization ID for scoping label searches

    Returns:
        List of (resource_id, resource_type) tuples
    """
    targets = []

    # Add explicit project targets
    if "target_projects" in action:
        for project_id in action["target_projects"]:
            targets.append((project_id, "project"))

    # Add explicit folder targets
    if "target_folders" in action:
        for folder_id in action["target_folders"]:
            targets.append((folder_id, "folder"))

    # Add organization target
    if "target_organization" in action:
        org_id = action["target_organization"]
        targets.append((org_id, "organization"))

    # Add projects discovered by labels
    if "target_labels" in action:
        label_filters = action["target_labels"]
        discovered_projects = project_discovery.find_projects_by_labels(label_filters)
        for project_id in discovered_projects:
            targets.append((project_id, "project"))

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

                email_budget_data = {
                    "cost_amount": cost_amount,
                    "budget_amount": budget_amount,
                    "threshold_percent": threshold_percent,
                    "billing_account_id": attributes.get("billingAccountId", "unknown"),
                    "budget_id": attributes.get("budgetId", "unknown"),
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
            for resource_id, resource_type in targets:
                if action_type == "restrict_services":
                    services = action.get("services", [])
                    response_engine.apply_service_restriction(
                        resource_id, services, action="deny", resource_type=resource_type
                    )
                    executed_actions.append(
                        {
                            "type": action_type,
                            "resource_id": resource_id,
                            "resource_type": resource_type,
                            "details": f"Restricted services: {', '.join(services)}",
                        }
                    )

                elif action_type == "apply_constraint":
                    constraint = action.get("constraint")
                    enforce = action.get("enforce", True)
                    values = action.get("values")
                    response_engine.apply_custom_constraint(
                        resource_id, constraint, enforce, values, resource_type=resource_type
                    )
                    executed_actions.append(
                        {
                            "type": action_type,
                            "resource_id": resource_id,
                            "resource_type": resource_type,
                            "details": f"Applied constraint: {constraint}",
                        }
                    )

                elif action_type == "log_only":
                    logger.warning(
                        "Log-only action for %s %s: %s",
                        resource_type,
                        resource_id,
                        action.get("message", "Budget threshold exceeded"),
                    )
                    executed_actions.append(
                        {
                            "type": action_type,
                            "resource_id": resource_id,
                            "resource_type": resource_type,
                            "details": action.get("message", "Budget threshold exceeded"),
                        }
                    )

                else:
                    logger.warning("Unknown action type: %s", action_type)

        logger.info("Budget response processing completed")

    except Exception as e:
        logger.error("Error processing budget alert: %s", e, exc_info=True)
        raise
