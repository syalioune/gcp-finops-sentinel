#!/usr/bin/env python3
"""
Script to publish test budget alert events to Pub/Sub emulator.

This script publishes sample budget alert messages to test the GCP FinOps Sentinel
function locally using the Pub/Sub emulator.

Usage:
    # Basic usage (uses defaults)
    PUBSUB_EMULATOR_HOST=localhost:8681 python publish-budget-alert-event.py

    # Custom budget amounts
    PUBSUB_EMULATOR_HOST=localhost:8681 python publish-budget-alert-event.py --budget=1000 --cost=900

    # Multiple test scenarios
    python publish-budget-alert-event.py --scenario=critical  # 100% threshold
    python publish-budget-alert-event.py --scenario=high      # 90% threshold
    python publish-budget-alert-event.py --scenario=warning   # 80% threshold
"""

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict

from google.cloud import pubsub_v1

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


# Predefined test scenarios with realistic billing account IDs and budget UUIDs
SCENARIOS = {
    "critical": {
        "budget": 1000,
        "cost": 1000,
        "billing_account_id": "012345-6789AB-CDEF01",
        "budget_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        "description": "Critical threshold (100%)",
    },
    "high": {
        "budget": 1000,
        "cost": 900,
        "billing_account_id": "012345-6789AB-CDEF01",
        "budget_id": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
        "description": "High threshold (90%)",
    },
    "warning": {
        "budget": 1000,
        "cost": 800,
        "billing_account_id": "FEDCBA-987654-321098",
        "budget_id": "b2c3d4e5-f6a7-4b5c-9d0e-1f2a3b4c5d6e",
        "description": "Warning threshold (80%)",
    },
    "dev": {
        "budget": 1000,
        "cost": 750,
        "billing_account_id": "012345-6789AB-CDEF01",
        "budget_id": "c3d4e5f6-a7b8-4c5d-0e1f-2a3b4c5d6e7f",
        "description": "Dev account threshold (75%)",
    },
}


def create_budget_alert_data(
    budget_amount: float,
    cost_amount: float,
    budget_name: str = "Test Budget Alert",
) -> Dict[str, Any]:
    """
    Create a budget alert message payload.

    Args:
        budget_amount: Total budget amount
        cost_amount: Current cost amount
        budget_name: Budget display name

    Returns:
        Budget alert data dictionary
    """
    return {
        "costAmount": cost_amount,
        "budgetAmount": budget_amount,
        "budgetDisplayName": budget_name,
    }


def publish_message(
    project_id: str,
    topic_name: str,
    message_data: Dict[str, Any],
    billing_account_id: str,
    budget_id: str,
) -> None:
    """
    Publish a message to a Pub/Sub topic with attributes.

    Args:
        project_id: GCP project ID
        topic_name: Pub/Sub topic name
        message_data: Message payload to publish
        billing_account_id: Billing account ID (message attribute)
        budget_id: Budget ID UUID (message attribute)
    """
    # Create publisher client
    publisher = pubsub_v1.PublisherClient()
    topic_path = publisher.topic_path(project_id, topic_name)

    # Ensure topic exists
    try:
        publisher.get_topic(request={"topic": topic_path})
        logger.info(f"Using existing topic: {topic_path}")
    except Exception:
        logger.info(f"Creating topic: {topic_path}")
        publisher.create_topic(request={"name": topic_path})

    # Publish message with attributes
    message_json = json.dumps(message_data)
    message_bytes = message_json.encode("utf-8")

    # Add billingAccountId and budgetId as message attributes
    attributes = {
        "billingAccountId": billing_account_id,
        "budgetId": budget_id,
    }

    future = publisher.publish(topic_path, message_bytes, **attributes)
    message_id = future.result()

    logger.info(f"✓ Published message ID: {message_id}")


def main():
    """Main function to publish test budget alert events."""
    parser = argparse.ArgumentParser(
        description="Publish test budget alert events to Pub/Sub emulator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Scenario-based testing
    parser.add_argument(
        "--scenario",
        choices=list(SCENARIOS.keys()),
        help="Use predefined test scenario",
    )

    # Custom values
    parser.add_argument(
        "--budget",
        type=float,
        help="Budget amount (default: 1000)",
    )
    parser.add_argument(
        "--cost",
        type=float,
        help="Current cost amount (default: 900)",
    )
    parser.add_argument(
        "--billing-account",
        help="Billing account ID (default: 012345-6789AB-CDEF01)",
    )
    parser.add_argument(
        "--budget-id",
        help="Budget ID UUID (default: generated UUID)",
    )

    # Pub/Sub configuration
    parser.add_argument(
        "--pubsub-project",
        default=os.getenv("PUBSUB_PROJECT_ID", "local-gcp-test-project"),
        help="Pub/Sub project ID (default: local-gcp-test-project)",
    )
    parser.add_argument(
        "--topic",
        default=os.getenv("BUDGET_TOPIC", "billing-alerts"),
        help="Pub/Sub topic name (default: billing-alerts)",
    )

    args = parser.parse_args()

    # Check for emulator
    emulator_host = os.getenv("PUBSUB_EMULATOR_HOST")
    if emulator_host:
        logger.info(f"Using Pub/Sub emulator: {emulator_host}")
    else:
        logger.warning("⚠️  PUBSUB_EMULATOR_HOST not set - will use production Pub/Sub")
        response = input("Continue? [y/N]: ")
        if response.lower() != "y":
            logger.info("Aborted")
            sys.exit(0)

    # Determine values to use
    if args.scenario:
        scenario = SCENARIOS[args.scenario]
        budget_amount = scenario["budget"]
        cost_amount = scenario["cost"]
        billing_account_id = scenario["billing_account_id"]
        budget_id = scenario["budget_id"]
        logger.info(f"Using scenario: {args.scenario} - {scenario['description']}")
    else:
        budget_amount = args.budget or 1000
        cost_amount = args.cost or 900
        billing_account_id = args.billing_account or "012345-6789AB-CDEF01"
        budget_id = args.budget_id or "f47ac10b-58cc-4372-a567-0e02b2c3d479"

    # Calculate percentage
    percentage = (cost_amount / budget_amount) * 100

    # Create budget alert data
    budget_data = create_budget_alert_data(
        budget_amount=budget_amount,
        cost_amount=cost_amount,
    )

    # Display information
    logger.info("")
    logger.info("Publishing test budget alert event:")
    logger.info(f"  Budget Amount:       ${budget_amount:.2f}")
    logger.info(f"  Cost Amount:         ${cost_amount:.2f}")
    logger.info(f"  Percentage:          {percentage:.1f}%")
    logger.info(f"  Billing Account ID:  {billing_account_id}")
    logger.info(f"  Budget ID:           {budget_id}")
    logger.info("")
    logger.info("Budget Alert Data:")
    logger.info(json.dumps(budget_data, indent=2))
    logger.info("")
    logger.info("Message Attributes:")
    logger.info(
        json.dumps({"billingAccountId": billing_account_id, "budgetId": budget_id}, indent=2)
    )
    logger.info("")

    # Publish message
    try:
        publish_message(
            project_id=args.pubsub_project,
            topic_name=args.topic,
            message_data=budget_data,
            billing_account_id=billing_account_id,
            budget_id=budget_id,
        )
        logger.info("")
        logger.info("✓ Test event published successfully!")

    except Exception as e:
        logger.error(f"❌ Failed to publish message: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
