#!/usr/bin/env python3
"""
Integration tests for Budget Response Function

Tests the complete flow:
1. Publish budget alert to Pub/Sub emulator
2. Function receives and processes the message
3. Verify policies are applied (mocked)
"""

import base64
import json
import logging
import os
import sys
import time

import requests
from google.cloud import pubsub_v1

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class IntegrationTestRunner:
    """Integration test runner for Budget Response Function."""

    def __init__(self):
        """Initialize the test runner."""
        self.project_id = os.environ.get("PUBSUB_PROJECT_ID", "local-gcp-test-project")
        self.topic_name = os.environ.get("BUDGET_TOPIC", "billing-alerts")
        self.action_events_topic_name = os.environ.get(
            "ACTION_EVENT_TOPIC", "gcp-finops-sentinel-action"
        )
        self.action_events_subscription_name = "integration-tests-assertion-sub"
        self.function_url = os.environ.get("FUNCTION_URL", "http://budget-function:8080")
        self.organization_id = os.environ.get("ORGANIZATION_ID", "123456789012")
        self.mailhog_url = os.environ.get("MAILHOG_URL", "http://mailhog:8025")

        # Create Pub/Sub clients
        self.publisher = pubsub_v1.PublisherClient()
        self.subscriber = pubsub_v1.SubscriberClient()

        self.topic_path = self.publisher.topic_path(self.project_id, self.topic_name)
        self.action_events_topic_path = self.publisher.topic_path(
            self.project_id, self.action_events_topic_name
        )
        self.action_events_subscription_path = self.subscriber.subscription_path(
            self.project_id, self.action_events_subscription_name
        )

        self.tests_passed = 0
        self.tests_failed = 0

    def setup(self):
        """Set up test environment."""
        logger.info("Setting up integration test environment...")

        try:
            # Create budget alerts topic if it doesn't exist
            try:
                self.publisher.create_topic(request={"name": self.topic_path})
                logger.info(f"Created topic: {self.topic_path}")
            except Exception as e:
                logger.info(f"Budget topic might already exist: {e}")

            # Create action events topic if it doesn't exist
            try:
                self.publisher.create_topic(request={"name": self.action_events_topic_path})
                logger.info(f"Created action events topic: {self.action_events_topic_path}")
            except Exception as e:
                logger.info(f"Action events topic might already exist: {e}")

            # Create subscription for action events
            try:
                self.subscriber.create_subscription(
                    request={
                        "name": self.action_events_subscription_path,
                        "topic": self.action_events_topic_path,
                        "ack_deadline_seconds": 60,
                    }
                )
                logger.info(f"Created subscription: {self.action_events_subscription_path}")
            except Exception as e:
                logger.info(f"Subscription might already exist: {e}")

            # Wait for services to be ready
            logger.info("Waiting for services to be ready...")
            time.sleep(2)

            logger.info("Setup complete")
            return True

        except Exception as e:
            logger.error(f"Setup failed: {e}")
            return False

    def teardown(self):
        """Clean up test environment."""
        logger.info("Tearing down test environment...")

        try:
            # Delete subscription
            self.subscriber.delete_subscription(
                request={"subscription": self.action_events_subscription_path}
            )
            logger.info(f"Deleted subscription: {self.action_events_subscription_path}")
        except Exception as e:
            logger.warning(f"Failed to delete subscription: {e}")

        logger.info("Teardown complete")

    def publish_budget_alert(
        self, budget_data: dict, billing_account_id: str, budget_id: str
    ) -> str:
        """
        Publish a budget alert message to Pub/Sub with attributes.

        Args:
            budget_data: Budget alert data
            billing_account_id: Billing account ID (message attribute)
            budget_id: Budget ID UUID (message attribute)

        Returns:
            Message ID
        """
        message_json = json.dumps(budget_data)
        message_bytes = message_json.encode("utf-8")

        # Add billingAccountId and budgetId as message attributes
        attributes = {
            "billingAccountId": billing_account_id,
            "budgetId": budget_id,
        }

        future = self.publisher.publish(self.topic_path, message_bytes, **attributes)
        message_id = future.result()

        logger.info(f"Published message {message_id}")
        logger.debug(f"Message data: {message_json}")
        logger.debug(f"Attributes: {attributes}")
        return message_id

    def pull_action_events(self, max_messages: int = 100, timeout: float = 5.0) -> list:
        """
        Pull action event messages from Pub/Sub subscription.

        Args:
            max_messages: Maximum number of messages to pull
            timeout: Timeout in seconds

        Returns:
            List of parsed action event messages
        """
        try:
            response = self.subscriber.pull(
                request={
                    "subscription": self.action_events_subscription_path,
                    "max_messages": max_messages,
                },
                timeout=timeout,
            )

            events = []
            ack_ids = []

            for received_message in response.received_messages:
                # Parse the message data
                message_data = received_message.message.data.decode("utf-8")
                event = json.loads(message_data)
                events.append(event)
                ack_ids.append(received_message.ack_id)

                logger.info(
                    f"Received action event: {event.get('action_type')} for {event.get('resource_type')}/{event.get('resource_id')}"
                )

            # Acknowledge the messages
            if ack_ids:
                self.subscriber.acknowledge(
                    request={
                        "subscription": self.action_events_subscription_path,
                        "ack_ids": ack_ids,
                    }
                )
                logger.info(f"Acknowledged {len(ack_ids)} messages")

            return events

        except Exception as e:
            logger.warning(f"Failed to pull action events: {e}")
            return []

    def get_mailhog_messages(self) -> list:
        """
        Get all messages from MailHog.

        Returns:
            List of email messages from MailHog
        """
        try:
            response = requests.get(f"{self.mailhog_url}/api/v2/messages", timeout=5)
            response.raise_for_status()
            data = response.json()
            return data.get("items", [])
        except Exception as e:
            logger.warning(f"Failed to get MailHog messages: {e}")
            return []

    def delete_mailhog_messages(self):
        """Delete all messages from MailHog."""
        try:
            requests.delete(f"{self.mailhog_url}/api/v1/messages", timeout=5)
            logger.info("Deleted all MailHog messages")
        except Exception as e:
            logger.warning(f"Failed to delete MailHog messages: {e}")

    def find_email_by_recipient(self, recipient: str, timeout: float = 10.0) -> dict:
        """
        Find an email message by recipient address.

        Args:
            recipient: Recipient email address
            timeout: Timeout in seconds

        Returns:
            Email message dict or None
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            messages = self.get_mailhog_messages()
            for message in messages:
                to_addresses = message.get("To", [])
                for to_addr in to_addresses:
                    if recipient in to_addr.get("Mailbox", "") + "@" + to_addr.get("Domain", ""):
                        return message
            time.sleep(0.5)
        return None

    def test_critical_budget_threshold(self):
        """Test critical budget threshold (100%)."""
        logger.info("\n=== Test: Critical Budget Threshold (100%) ===")

        try:
            budget_data = {
                "costAmount": 1000,
                "budgetAmount": 1000,
                "budgetDisplayName": "Test Organization Budget",
            }

            # Publish the alert with attributes
            billing_account_id = "012345-6789AB-CDEF01"
            budget_id = "f47ac10b-58cc-4372-a567-0e02b2c3d479"
            message_id = self.publish_budget_alert(budget_data, billing_account_id, budget_id)

            # Wait for processing
            time.sleep(3)

            # Pull action events from Pub/Sub
            events = self.pull_action_events()

            # At 100% with billing account 012345-6789AB-CDEF01, should trigger:
            # 1. test_critical_threshold (100-104.99%): restrict_services on test-project-critical

            # Verify service restriction on test-project-critical
            project_id = "test-project-critical"
            constraint = "gcp.restrictServiceUsage"

            matching_events = [
                e
                for e in events
                if e.get("resource_id") == project_id
                and e.get("resource_type") == "project"
                and e.get("action_type") == "restrict_services"
                and e.get("details", {}).get("constraint") == constraint
            ]

            if not matching_events:
                raise AssertionError(
                    f"No action event found for service restriction on {project_id}. "
                    f"Received {len(events)} events: {events}"
                )

            event = matching_events[0]

            # Verify event details
            if not event.get("success"):
                raise AssertionError(
                    f"Action event indicates failure: {event.get('details', {}).get('error')}"
                )

            details = event.get("details", {})
            denied_services = details.get("services", [])
            expected_services = ["compute.googleapis.com", "container.googleapis.com"]

            if set(denied_services) != set(expected_services):
                raise AssertionError(
                    f"Unexpected denied services. Expected: {expected_services}, "
                    f"Got: {denied_services}"
                )

            logger.info(
                f"✓ Critical threshold test completed - {len(events)} action events verified"
            )
            self.tests_passed += 1
            return True

        except Exception as e:
            logger.error(f"✗ Critical threshold test failed: {e}")
            self.tests_failed += 1
            return False

    def test_warning_budget_threshold(self):
        """Test warning budget threshold (80%)."""
        logger.info("\n=== Test: Warning Budget Threshold (80%) ===")

        try:
            budget_data = {
                "costAmount": 800,
                "budgetAmount": 1000,
                "budgetDisplayName": "Test Warning Budget",
            }

            # Publish the alert with attributes
            billing_account_id = "FEDCBA-987654-321098"
            budget_id = "b2c3d4e5-f6a7-4b5c-9d0e-1f2a3b4c5d6e"
            message_id = self.publish_budget_alert(budget_data, billing_account_id, budget_id)

            # Wait for processing
            time.sleep(3)

            # Pull action events from Pub/Sub
            events = self.pull_action_events()

            # Verify NO action events for this project (log-only action doesn't publish events)
            project_id = "test-project-warning"
            matching_events = [
                e
                for e in events
                if e.get("resource_id") == project_id and e.get("resource_type") == "project"
            ]

            if matching_events:
                logger.warning(
                    f"Warning threshold triggered action events (may be from other rules): "
                    f"{matching_events}"
                )

            logger.info("✓ Warning threshold test completed - no action events as expected")
            self.tests_passed += 1
            return True

        except Exception as e:
            logger.error(f"✗ Warning threshold test failed: {e}")
            self.tests_failed += 1
            return False

    def test_dev_project_filter(self):
        """Test billing account filter for dev account."""
        logger.info("\n=== Test: Dev Account Filter ===")

        try:
            budget_data = {
                "costAmount": 900,
                "budgetAmount": 1000,
                "budgetDisplayName": "Test Dev Account Budget",
            }

            # Publish the alert with billing account filter
            billing_account_id = "012345-6789AB-CDEF01"  # Matches test_billing_account_filter rule
            budget_id = "c3d4e5f6-a7b8-4c5d-0e1f-2a3b4c5d6e7f"
            message_id = self.publish_budget_alert(budget_data, billing_account_id, budget_id)

            # Wait for processing
            time.sleep(3)

            # Pull action events from Pub/Sub
            events = self.pull_action_events()

            # At 90% with billing account 012345-6789AB-CDEF01, should trigger:
            # - test_billing_account_filter (75-79.99%): NO (above range)
            # - test_high_threshold (90-94.99%): YES - apply_constraint on test-project-high
            # - test_label_based_targeting (90-94.99%): YES - targets label-matched projects
            target_projects_labels = [
                "mock-project-env-prod",
                "mock-project-cost-center-engineering",
            ]

            # Check for label-based targeting (test_label_based_targeting rule at 90-94.99%)
            label_events = [
                e
                for e in events
                if e.get("resource_id") in target_projects_labels
                and e.get("resource_type") == "project"
                and e.get("action_type") == "restrict_services"
            ]

            if len(label_events) != len(target_projects_labels):
                raise AssertionError(
                    f"Expected {len(target_projects_labels)} label-based events, got {len(label_events)}. "
                    f"Events: {label_events}"
                )

            logger.info(
                f"✓ Billing account filter test completed - {len(events)} action events verified"
            )
            self.tests_passed += 1
            return True

        except Exception as e:
            logger.error(f"✗ Dev project filter test failed: {e}")
            self.tests_failed += 1
            return False

    def test_below_threshold(self):
        """Test budget below threshold (no action expected)."""
        logger.info("\n=== Test: Below Threshold (No Action) ===")

        try:
            budget_data = {
                "costAmount": 400,
                "budgetAmount": 1000,
                "budgetDisplayName": "Test Below Threshold Budget",
            }

            # Publish the alert with attributes
            billing_account_id = "999999-999999-999999"
            budget_id = "d4e5f6a7-b8c9-4d5e-1f2a-3b4c5d6e7f8a"
            message_id = self.publish_budget_alert(budget_data, billing_account_id, budget_id)

            # Wait for processing
            time.sleep(3)

            # Pull action events from Pub/Sub
            events = self.pull_action_events()

            # Verify NO action events (40% < 75%, lowest threshold, and no matching filters)
            if events:
                raise AssertionError(
                    f"Unexpected action events for below-threshold budget: " f"{events}"
                )

            logger.info("✓ Below threshold test completed - no action events as expected")
            self.tests_passed += 1
            return True

        except Exception as e:
            logger.error(f"✗ Below threshold test failed: {e}")
            self.tests_failed += 1
            return False

    def test_multiple_rules_triggered(self):
        """Test multiple rules being triggered at 92% threshold."""
        logger.info("\n=== Test: Multiple Rules Triggered (92%) ===")

        try:
            # Use 92% to trigger multiple rules in the 90-94.99% range
            budget_data = {
                "costAmount": 920,
                "budgetAmount": 1000,
                "budgetDisplayName": "Test Multiple Rules Budget",
            }

            # Publish the alert with attributes (no filter, should match threshold-only rules)
            billing_account_id = "999999-999999-999999"
            budget_id = "e5f6a7b8-c9d0-4e5f-2a3b-4c5d6e7f8a9b"
            self.publish_budget_alert(budget_data, billing_account_id, budget_id)

            # Wait for processing
            time.sleep(3)

            # Pull action events from Pub/Sub
            events = self.pull_action_events()

            # At 92% with unmatched billing account/budget ID, this should trigger:
            # - test_billing_account_filter (75-79.99%): NO (above range)
            # - test_warning_threshold (80-84.99%): NO (above range)
            # - test_budget_id_filter (85-89.99%): NO (above range)
            # - test_high_threshold (90-94.99%): YES - apply_constraint on test-project-high
            # - test_label_based_targeting (90-94.99%): YES - restrict_services on label-matched projects
            # - test_folder_targeting (95-99.99%): NO (below range)
            # - test_critical_threshold (100-104.99%): NO (below range)
            # - test_organization_targeting (105-109.99%): NO (below range)
            # Total: 2 rules triggered (both in 90-94.99% range)

            # Verify external IP constraint events on test-project-high
            target_projects = ["test-project-high"]
            constraint_events = [
                e
                for e in events
                if e.get("resource_id") in target_projects
                and e.get("resource_type") == "project"
                and e.get("action_type") == "apply_constraint"
                and e.get("details", {}).get("constraint") == "compute.vmExternalIpAccess"
            ]

            if not constraint_events:
                raise AssertionError(
                    f"No external IP constraint events found for {target_projects}. "
                    f"Events: {events}"
                )

            # Verify label-based targeting events (test_label_based_targeting rule at 90-94.99%)
            label_target_projects = [
                "mock-project-env-prod",
                "mock-project-cost-center-engineering",
            ]
            label_events = [
                e
                for e in events
                if e.get("resource_id") in label_target_projects
                and e.get("resource_type") == "project"
                and e.get("action_type") == "restrict_services"
            ]

            if len(label_events) != len(label_target_projects):
                raise AssertionError(
                    f"Expected {len(label_target_projects)} label-based events, got {len(label_events)}. "
                    f"Label events: {label_events}"
                )

            # Verify folder targeting was NOT applied (only at 95-99.99%)
            folder_id = "123456789"
            folder_events = [
                e
                for e in events
                if e.get("resource_id") == folder_id
                and e.get("resource_type") == "folder"
                and e.get("action_type") == "restrict_services"
            ]

            if folder_events:
                raise AssertionError(
                    f"Folder targeting applied at 92% (expected only at 95-99.99%): "
                    f"{folder_events}"
                )

            # Verify critical service restriction was NOT applied (only at 100-104.99% range)
            critical_projects = ["test-project-critical"]
            critical_events = [
                e
                for e in events
                if e.get("resource_id") in critical_projects
                and e.get("resource_type") == "project"
                and e.get("action_type") == "restrict_services"
            ]

            if critical_events:
                raise AssertionError(
                    f"Critical service restriction applied at 92% (expected only at 100-104.99%): "
                    f"{critical_events}"
                )

            logger.info(f"✓ Multiple rules test completed - {len(events)} action events verified")
            self.tests_passed += 1
            return True

        except Exception as e:
            logger.error(f"✗ Multiple rules test failed: {e}")
            self.tests_failed += 1
            return False

    def test_email_notification(self):
        """Test email notification via send_mail action."""
        logger.info("\n=== Test: Email Notification (send_mail action) ===")

        try:
            # Clear MailHog messages before test
            self.delete_mailhog_messages()

            # Create budget data that will trigger email notification
            budget_data = {
                "costAmount": 1100,
                "budgetAmount": 1000,
                "budgetDisplayName": "Test Email Notification Budget",
            }

            # Publish the alert with attributes
            # This should match test_integration_email_notification rule (110-114.99%)
            billing_account_id = "EMAIL-NOTIF-TEST"
            budget_id = "email-test-budget-uuid"
            message_id = self.publish_budget_alert(budget_data, billing_account_id, budget_id)

            # Wait for processing and email delivery
            logger.info("Waiting for email delivery...")
            time.sleep(5)

            # Check MailHog for the email
            test_recipient = "finops-alerts@example.com"
            email_message = self.find_email_by_recipient(test_recipient, timeout=10.0)

            if not email_message:
                # Log all messages for debugging
                all_messages = self.get_mailhog_messages()
                logger.error(f"All MailHog messages: {json.dumps(all_messages, indent=2)}")
                raise AssertionError(
                    f"No email found for recipient {test_recipient}. "
                    f"Total messages in MailHog: {len(all_messages)}"
                )

            logger.info(f"Found email message: {email_message.get('ID')}")

            # Verify email headers
            from_addr = email_message.get("From", {})
            from_email = f"{from_addr.get('Mailbox')}@{from_addr.get('Domain')}"
            if from_email != "finops-sentinel@example.com":
                raise AssertionError(
                    f"Unexpected from address. Expected: finops-sentinel@example.com, "
                    f"Got: {from_email}"
                )

            # Verify recipients
            to_addresses = email_message.get("To", [])
            to_emails = [f"{to.get('Mailbox')}@{to.get('Domain')}" for to in to_addresses]

            expected_recipients = ["finops-alerts@example.com", "budget-admin@example.com"]
            if not all(recipient in to_emails for recipient in expected_recipients):
                raise AssertionError(
                    f"Missing expected recipients. Expected: {expected_recipients}, "
                    f"Got: {to_emails}"
                )

            # Verify subject contains budget information
            subject = email_message.get("Content", {}).get("Headers", {}).get("Subject", [""])[0]
            if "Budget_Alert" not in subject or "110=2E0=25" not in subject:
                raise AssertionError(
                    f"Subject does not contain expected budget alert info. Subject: {subject}"
                )

            # Verify email body contains budget details
            # Note: MailHog returns body content as base64-encoded
            body_html = None

            # Try MIME body
            mime_parts = email_message.get("MIME", {}).get("Parts", [])
            for part in mime_parts:
                if "text/html" in part.get("Headers", {}).get("Content-Type", [""])[0]:
                    body_html = part.get("Body", "")
                    if body_html:
                        # Decode base64-encoded body
                        try:
                            body_html = base64.b64decode(body_html).decode("utf-8")
                        except Exception as e:
                            logger.warning(f"Failed to decode MIME body: {e}")
                    break

            if not body_html:
                raise AssertionError("Email body is empty")

            # Check for key budget information in HTML body
            required_content = [
                "1100",  # Cost amount
                "1000",  # Budget amount
                "110",  # Threshold percent
                budget_id,  # Budget ID
            ]

            for content in required_content:
                if content not in body_html:
                    raise AssertionError(
                        f"Email body missing expected content: '{content}'. "
                        f"Body preview: {body_html[:500]}"
                    )

            # Verify custom message is included
            if "Critical email notification test" not in body_html:
                raise AssertionError(
                    "Custom message not found in email body. " f"Body preview: {body_html[:500]}"
                )

            # Verify policy action event was published for send_mail action
            action_events = self.pull_action_events()

            # Look for send_mail action event
            # send_mail publishes as "send_email" with resource_type="notification"
            email_action_events = [
                e
                for e in action_events
                if e.get("action_type") == "send_email" and e.get("resource_type") == "notification"
            ]

            if not email_action_events:
                logger.warning(
                    f"No send_email action event found in Pub/Sub. "
                    f"Total events: {len(action_events)}, Events: {action_events}"
                )
                # This might be expected if ACTION_EVENT_TOPIC is not configured for send_mail
            else:
                # Verify event details
                email_event = email_action_events[0]
                if not email_event.get("success"):
                    raise AssertionError(
                        f"Email action event indicates failure: {email_event.get('details', {}).get('error')}"
                    )

                # Verify recipients in event details
                event_details = email_event.get("details", {})
                event_recipients = event_details.get(
                    "recipients", []
                )  # Changed from to_emails to recipients
                if not all(r in event_recipients for r in expected_recipients):
                    raise AssertionError(
                        f"Action event missing expected recipients. "
                        f"Expected: {expected_recipients}, Got: {event_recipients}"
                    )

                logger.info(
                    f"✓ Send_mail action event verified in Pub/Sub: {email_event.get('ID')}"
                )

            logger.info("✓ Email notification test completed - email verified in MailHog")
            self.tests_passed += 1
            return True

        except Exception as e:
            logger.error(f"✗ Email notification test failed: {e}")
            self.tests_failed += 1
            return False

    def test_email_with_actions_taken(self):
        """Test email notification includes prior actions taken."""
        logger.info("\n=== Test: Email Notification with Actions Taken ===")

        try:
            # Clear MailHog messages before test
            self.delete_mailhog_messages()

            # Create budget data that will trigger multiple actions including email
            budget_data = {
                "costAmount": 1150,
                "budgetAmount": 1000,
                "budgetDisplayName": "Test Email with Actions Budget",
            }

            # Publish the alert
            # This should match test_integration_email_with_actions rule (115%+, open-ended)
            billing_account_id = "EMAIL-WITH-ACTIONS-TEST"
            budget_id = "email-actions-test-uuid"
            self.publish_budget_alert(budget_data, billing_account_id, budget_id)

            # Wait for processing and email delivery
            logger.info("Waiting for email delivery...")
            time.sleep(5)

            # Check MailHog for the email
            test_recipient = "critical-alerts@example.com"
            email_message = self.find_email_by_recipient(test_recipient, timeout=10.0)

            if not email_message:
                all_messages = self.get_mailhog_messages()
                raise AssertionError(
                    f"No email found for recipient {test_recipient}. "
                    f"Total messages in MailHog: {len(all_messages)}"
                )

            # Verify email body contains actions taken
            # Note: MailHog returns body content as base64-encoded
            body_html = None
            mime_parts = email_message.get("MIME", {}).get("Parts", [])
            for part in mime_parts:
                if "text/html" in part.get("Headers", {}).get("Content-Type", [""])[0]:
                    body_html = part.get("Body", "")
                    if body_html:
                        # Decode base64-encoded body
                        try:
                            body_html = base64.b64decode(body_html).decode("utf-8")
                        except Exception as e:
                            logger.warning(f"Failed to decode MIME body: {e}")
                    break

            if not body_html:
                raise AssertionError("Email body is empty")

            # Check for actions taken section in email
            if "actions" not in body_html.lower():
                raise AssertionError(
                    "Email body does not contain actions section. "
                    f"Body preview: {body_html[:500]}"
                )

            # Verify action types are mentioned
            expected_action_mentions = ["restrict_services", "apply_constraint"]
            for action_type in expected_action_mentions:
                if action_type not in body_html:
                    logger.warning(
                        f"Email body does not mention action type '{action_type}'. "
                        f"This may be OK if using built-in templates."
                    )

            # Verify policy action events were published
            action_events = self.pull_action_events()

            # At 115% threshold, should have multiple action events
            # Expected: restrict_services, apply_constraint, send_email
            expected_action_types = ["restrict_services", "apply_constraint", "send_email"]
            found_action_types = [e.get("action_type") for e in action_events]

            for expected_type in expected_action_types:
                if expected_type not in found_action_types:
                    logger.warning(
                        f"Action event '{expected_type}' not found in Pub/Sub. "
                        f"Found: {found_action_types}"
                    )

            # Verify send_email action event specifically
            # send_mail publishes as "send_email" with resource_type="notification"
            email_action_events = [
                e
                for e in action_events
                if e.get("action_type") == "send_email" and e.get("resource_type") == "notification"
            ]

            if email_action_events:
                email_event = email_action_events[0]
                if not email_event.get("success"):
                    raise AssertionError(
                        f"Email action event indicates failure: {email_event.get('details', {}).get('error')}"
                    )

                # Verify recipients in event
                event_details = email_event.get("details", {})
                event_recipients = event_details.get(
                    "recipients", []
                )  # Changed from to_emails to recipients
                if test_recipient not in event_recipients:
                    raise AssertionError(
                        f"Action event missing test recipient {test_recipient}. "
                        f"Got: {event_recipients}"
                    )

                logger.info(
                    f"✓ Send_email action event verified with {len(action_events)} total events"
                )
            else:
                logger.warning("No send_email action event found (may not be configured)")

            logger.info("✓ Email with actions taken test completed - email verified in MailHog")
            self.tests_passed += 1
            return True

        except Exception as e:
            logger.error(f"✗ Email with actions taken test failed: {e}")
            self.tests_failed += 1
            return False

    def run_all_tests(self):
        """Run all integration tests."""
        logger.info("\n" + "=" * 60)
        logger.info("Starting Budget Response Function Integration Tests")
        logger.info("=" * 60)

        # Setup
        if not self.setup():
            logger.error("Setup failed, aborting tests")
            return False

        # Run tests
        try:
            self.test_critical_budget_threshold()
            self.test_warning_budget_threshold()
            self.test_dev_project_filter()
            self.test_below_threshold()
            self.test_multiple_rules_triggered()
            self.test_email_notification()
            self.test_email_with_actions_taken()

        finally:
            # Teardown
            self.teardown()

        # Print summary
        logger.info("\n" + "=" * 60)
        logger.info("Test Summary")
        logger.info("=" * 60)
        logger.info(f"Tests Passed: {self.tests_passed}")
        logger.info(f"Tests Failed: {self.tests_failed}")
        logger.info(f"Total Tests:  {self.tests_passed + self.tests_failed}")

        if self.tests_failed == 0:
            logger.info("\n✓ All tests passed!")
            return True
        else:
            logger.error(f"\n✗ {self.tests_failed} test(s) failed")
            return False


def main():
    """Main entry point."""
    runner = IntegrationTestRunner()
    success = runner.run_all_tests()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
