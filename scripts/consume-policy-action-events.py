#!/usr/bin/env python3
"""


This script consume policy action events published by GCP FinOps Sentinel.

Usage:
    PUBSUB_EMULATOR_HOST=localhost:8681 python consume-policy-action-events.py --project=local-gcp-test-project --subscription=policy-action-events-sub
"""

import argparse
import json
import logging
import os
import sys
from typing import Any, Dict

from google.cloud import pubsub_v1

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def process_action_event(event_data: Dict[str, Any]) -> None:
    """
    Process a policy action event message.

    Args:
        event_data: Parsed event data from Pub/Sub message
    """

    log_to_audit_trail(event_data)

    action_type = event_data.get("action_type")
    project_id = event_data.get("project_id")
    success = event_data.get("success")
    details = event_data.get("details", {})

    # Log the event
    status = "✅ SUCCESS" if success else "❌ FAILED"
    logger.info(f"{status}: {action_type} on {project_id}")

    # Handle different action types
    if action_type == "restrict_services":
        services = details.get("services", [])
        logger.info(f"  Restricted services: {', '.join(services)}")

    elif action_type == "apply_constraint":
        constraint = details.get("constraint")
        enforce = details.get("enforce")
        logger.info(f"  Applied constraint: {constraint} (enforce={enforce})")

    # Handle failures
    if not success:
        error = details.get("error")
        logger.error(f"  Error: {error}")


def log_to_audit_trail(event_data: Dict[str, Any]) -> None:
    """
    Log event to audit trail (Cloud Logging, etc.)

    Args:
        event_data: Event data to log
    """

    logger.info(f"[AUDIT] {json.dumps(event_data)}")


def callback(message: pubsub_v1.subscriber.message.Message) -> None:
    """
    Callback function for processing Pub/Sub messages.

    Args:
        message: Pub/Sub message
    """
    try:
        # Parse message data
        event_data = json.loads(message.data.decode("utf-8"))

        # Process the event
        process_action_event(event_data)

        # Acknowledge the message
        message.ack()

    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        # Nack to retry
        message.nack()


def main():
    """Main function to subscribe to policy action events."""
    parser = argparse.ArgumentParser(description="Consume GCP FinOps Sentinel policy action events")
    parser.add_argument("--project", required=True, help="GCP Project ID")
    parser.add_argument("--subscription", required=True, help="Pub/Sub subscription name")
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

    # Create subscriber client
    subscriber = pubsub_v1.SubscriberClient()
    subscription_path = subscriber.subscription_path(args.project, args.subscription)

    logger.info(f"Listening for policy action events on {subscription_path}")

    # Subscribe to the topic
    streaming_pull_future = subscriber.subscribe(subscription_path, callback=callback)

    try:
        # Block and wait for messages
        streaming_pull_future.result()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        streaming_pull_future.cancel()
    except Exception as e:
        logger.error(f"Subscription error: {e}", exc_info=True)
        streaming_pull_future.cancel()


if __name__ == "__main__":
    main()
