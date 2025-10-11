"""
Unit tests for Budget Response Engine
"""

import json
import unittest
from unittest.mock import MagicMock, Mock, patch

from google.api_core.exceptions import NotFound

from budget_response_engine import BudgetResponseEngine


class TestBudgetResponseEngine(unittest.TestCase):
    """Test cases for the BudgetResponseEngine class."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = "123456789012"

    @patch("budget_response_engine.OrgPolicyClient")
    def test_apply_service_restriction(self, mock_client_class):
        """Test applying service restrictions."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        engine = BudgetResponseEngine(self.organization_id)

        result = engine.apply_service_restriction(
            "test-project", ["compute.googleapis.com"], action="deny"
        )

        # Should call get_policy and update_policy (upsert logic)
        self.assertTrue(mock_client.get_policy.called)
        self.assertTrue(mock_client.update_policy.called)
        self.assertTrue(result)

    @patch("budget_response_engine.OrgPolicyClient")
    def test_apply_custom_constraint_boolean(self, mock_client_class):
        """Test applying boolean constraint."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        engine = BudgetResponseEngine(self.organization_id)

        result = engine.apply_custom_constraint(
            "test-project", "compute.vmExternalIpAccess", enforce=True
        )

        # Should call get_policy and update_policy (upsert logic)
        self.assertTrue(mock_client.get_policy.called)
        self.assertTrue(mock_client.update_policy.called)
        self.assertTrue(result)

    @patch("budget_response_engine.OrgPolicyClient")
    def test_apply_custom_constraint_list(self, mock_client_class):
        """Test applying list constraint."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        engine = BudgetResponseEngine(self.organization_id)

        result = engine.apply_custom_constraint(
            "test-project",
            "compute.restrictMachineTypes",
            values=["n1-standard-1", "e2-micro"],
        )

        # Should call get_policy and update_policy (upsert logic)
        self.assertTrue(mock_client.get_policy.called)
        self.assertTrue(mock_client.update_policy.called)
        self.assertTrue(result)

    @patch("budget_response_engine.OrgPolicyClient")
    def test_apply_service_restriction_creates_policy_when_not_found(self, mock_client_class):
        """Test that service restriction creates policy when it doesn't exist."""
        mock_client = MagicMock()
        # Simulate policy not found - get_policy raises NotFound
        mock_client.get_policy.side_effect = NotFound("Policy not found")
        mock_client_class.return_value = mock_client

        engine = BudgetResponseEngine(self.organization_id)

        result = engine.apply_service_restriction(
            "test-project", ["compute.googleapis.com"], action="deny"
        )

        # Should call get_policy and create_policy (not update_policy)
        self.assertTrue(mock_client.get_policy.called)
        self.assertTrue(mock_client.create_policy.called)
        self.assertFalse(mock_client.update_policy.called)
        self.assertTrue(result)

    @patch("budget_response_engine.OrgPolicyClient")
    def test_apply_custom_constraint_creates_policy_when_not_found(self, mock_client_class):
        """Test that custom constraint creates policy when it doesn't exist."""
        mock_client = MagicMock()
        # Simulate policy not found - get_policy raises NotFound
        mock_client.get_policy.side_effect = NotFound("Policy not found")
        mock_client_class.return_value = mock_client

        engine = BudgetResponseEngine(self.organization_id)

        result = engine.apply_custom_constraint(
            "test-project", "compute.vmExternalIpAccess", enforce=True
        )

        # Should call get_policy and create_policy (not update_policy)
        self.assertTrue(mock_client.get_policy.called)
        self.assertTrue(mock_client.create_policy.called)
        self.assertFalse(mock_client.update_policy.called)
        self.assertTrue(result)

    @patch("budget_response_engine.OrgPolicyClient")
    def test_apply_service_restriction_error(self, mock_client_class):
        """Test error handling in service restriction."""
        mock_client = MagicMock()
        mock_client.update_policy.side_effect = Exception("API Error")
        mock_client_class.return_value = mock_client

        engine = BudgetResponseEngine(self.organization_id)

        result = engine.apply_service_restriction("test-project", ["compute.googleapis.com"])

        # Should return False on error
        self.assertFalse(result)

    @patch("budget_response_engine.PublisherClient")
    @patch("budget_response_engine.OrgPolicyClient")
    def test_event_publishing_on_successful_action(
        self, mock_org_client_class, mock_pub_client_class
    ):
        """Test that events are published when actions succeed."""
        mock_org_client = MagicMock()
        mock_org_client_class.return_value = mock_org_client

        mock_publisher = MagicMock()
        mock_future = MagicMock()
        mock_future.result.return_value = "msg-123"
        mock_publisher.publish.return_value = mock_future
        mock_pub_client_class.return_value = mock_publisher

        event_topic = "projects/test-project/topics/action-events"
        engine = BudgetResponseEngine(self.organization_id, event_topic=event_topic)

        result = engine.apply_service_restriction(
            "test-project", ["compute.googleapis.com"], action="deny"
        )

        # Should publish an event
        self.assertTrue(result)
        self.assertTrue(mock_publisher.publish.called)

        # Verify the published message structure
        call_args = mock_publisher.publish.call_args
        self.assertEqual(call_args[0][0], event_topic)

        # Parse the published data
        published_data = json.loads(call_args[0][1].decode("utf-8"))
        self.assertEqual(published_data["action_type"], "restrict_services")
        self.assertEqual(published_data["resource_id"], "test-project")
        self.assertEqual(published_data["resource_type"], "project")
        self.assertTrue(published_data["success"])
        self.assertEqual(published_data["organization_id"], self.organization_id)
        self.assertIn("details", published_data)
        self.assertIn("services", published_data["details"])

    @patch("budget_response_engine.PublisherClient")
    @patch("budget_response_engine.OrgPolicyClient")
    def test_event_publishing_on_failed_action(self, mock_org_client_class, mock_pub_client_class):
        """Test that events are published when actions fail."""
        mock_org_client = MagicMock()
        mock_org_client.update_policy.side_effect = Exception("Policy update failed")
        mock_org_client_class.return_value = mock_org_client

        mock_publisher = MagicMock()
        mock_future = MagicMock()
        mock_future.result.return_value = "msg-456"
        mock_publisher.publish.return_value = mock_future
        mock_pub_client_class.return_value = mock_publisher

        event_topic = "projects/test-project/topics/action-events"
        engine = BudgetResponseEngine(self.organization_id, event_topic=event_topic)

        result = engine.apply_service_restriction("test-project", ["compute.googleapis.com"])

        # Action should fail
        self.assertFalse(result)

        # But event should still be published
        self.assertTrue(mock_publisher.publish.called)

        # Verify the failure is recorded
        call_args = mock_publisher.publish.call_args
        published_data = json.loads(call_args[0][1].decode("utf-8"))
        self.assertFalse(published_data["success"])
        self.assertIsNotNone(published_data["details"]["error"])

    def test_no_event_publishing_when_topic_not_configured(self):
        """Test that events are not published when topic is not configured."""
        # Create engine without event_topic in dry-run mode
        engine = BudgetResponseEngine(self.organization_id, dry_run=True)

        # Verify publisher is not initialized
        self.assertIsNone(engine.publisher)

        result = engine.apply_service_restriction("test-project", ["compute.googleapis.com"])

        # Should succeed without publishing
        self.assertTrue(result)

    @patch("budget_response_engine.PublisherClient")
    @patch("budget_response_engine.OrgPolicyClient")
    def test_event_publishing_for_constraint_action(
        self, mock_org_client_class, mock_pub_client_class
    ):
        """Test event publishing for apply_constraint action."""
        mock_org_client = MagicMock()
        mock_org_client_class.return_value = mock_org_client

        mock_publisher = MagicMock()
        mock_future = MagicMock()
        mock_future.result.return_value = "msg-789"
        mock_publisher.publish.return_value = mock_future
        mock_pub_client_class.return_value = mock_publisher

        event_topic = "projects/test-project/topics/action-events"
        engine = BudgetResponseEngine(self.organization_id, event_topic=event_topic)

        result = engine.apply_custom_constraint(
            "test-project", "compute.vmExternalIpAccess", enforce=True
        )

        # Should publish an event
        self.assertTrue(result)
        self.assertTrue(mock_publisher.publish.called)

        # Verify the published message
        call_args = mock_publisher.publish.call_args
        published_data = json.loads(call_args[0][1].decode("utf-8"))
        self.assertEqual(published_data["action_type"], "apply_constraint")
        self.assertEqual(published_data["resource_id"], "test-project")
        self.assertEqual(published_data["resource_type"], "project")
        self.assertTrue(published_data["success"])
        self.assertEqual(
            published_data["details"]["constraint"],
            "compute.vmExternalIpAccess",
        )
        self.assertTrue(published_data["details"]["enforce"])

    def test_dry_run_mode_service_restriction(self):
        """Test that dry-run mode doesn't make real API calls for service restriction."""
        # Create engine in dry-run mode
        engine = BudgetResponseEngine(self.organization_id, dry_run=True)

        # Verify org_policy_client is None in dry-run mode
        self.assertIsNone(engine.org_policy_client)

        # Apply service restriction in dry-run mode
        result = engine.apply_service_restriction(
            "test-project", ["compute.googleapis.com"], action="deny"
        )

        # Should succeed without making API calls
        self.assertTrue(result)

    def test_dry_run_mode_custom_constraint(self):
        """Test that dry-run mode doesn't make real API calls for custom constraints."""
        # Create engine in dry-run mode
        engine = BudgetResponseEngine(self.organization_id, dry_run=True)

        # Verify org_policy_client is None in dry-run mode
        self.assertIsNone(engine.org_policy_client)

        # Apply custom constraint in dry-run mode
        result = engine.apply_custom_constraint(
            "test-project", "compute.vmExternalIpAccess", enforce=True
        )

        # Should succeed without making API calls
        self.assertTrue(result)

    @patch("budget_response_engine.PublisherClient")
    def test_dry_run_mode_with_event_publishing(self, mock_pub_client_class):
        """Test that dry-run mode still publishes action events when configured."""
        mock_publisher = MagicMock()
        mock_future = MagicMock()
        mock_future.result.return_value = "msg-dry-run"
        mock_publisher.publish.return_value = mock_future
        mock_pub_client_class.return_value = mock_publisher

        event_topic = "projects/test-project/topics/action-events"
        engine = BudgetResponseEngine(self.organization_id, event_topic=event_topic, dry_run=True)

        # Verify org_policy_client is None but publisher is initialized
        self.assertIsNone(engine.org_policy_client)
        self.assertIsNotNone(engine.publisher)

        # Apply service restriction in dry-run mode
        result = engine.apply_service_restriction("test-project", ["compute.googleapis.com"])

        # Should succeed and publish event
        self.assertTrue(result)
        self.assertTrue(mock_publisher.publish.called)

        # Verify the published message indicates success
        call_args = mock_publisher.publish.call_args
        published_data = json.loads(call_args[0][1].decode("utf-8"))
        self.assertEqual(published_data["action_type"], "restrict_services")
        self.assertTrue(published_data["success"])

    @patch("budget_response_engine.OrgPolicyClient")
    def test_apply_service_restriction_to_folder(self, mock_client_class):
        """Test applying service restrictions to a folder."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        engine = BudgetResponseEngine(self.organization_id)

        result = engine.apply_service_restriction(
            "123456789", ["compute.googleapis.com"], action="deny", resource_type="folder"
        )

        # Should call get_policy and update_policy (upsert logic)
        self.assertTrue(mock_client.get_policy.called)
        self.assertTrue(mock_client.update_policy.called)
        self.assertTrue(result)

        # Verify correct parent format for folder
        update_call_args = mock_client.update_policy.call_args
        policy = update_call_args.kwargs["policy"]
        self.assertTrue(policy.name.startswith("folders/123456789/policies/"))

    @patch("budget_response_engine.OrgPolicyClient")
    def test_apply_service_restriction_to_organization(self, mock_client_class):
        """Test applying service restrictions to an organization."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        engine = BudgetResponseEngine(self.organization_id)

        result = engine.apply_service_restriction(
            self.organization_id,
            ["compute.googleapis.com"],
            action="deny",
            resource_type="organization",
        )

        # Should call get_policy and update_policy (upsert logic)
        self.assertTrue(mock_client.get_policy.called)
        self.assertTrue(mock_client.update_policy.called)
        self.assertTrue(result)

        # Verify correct parent format for organization
        update_call_args = mock_client.update_policy.call_args
        policy = update_call_args.kwargs["policy"]
        self.assertTrue(policy.name.startswith(f"organizations/{self.organization_id}/policies/"))

    @patch("budget_response_engine.OrgPolicyClient")
    def test_apply_custom_constraint_to_folder(self, mock_client_class):
        """Test applying custom constraint to a folder."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        engine = BudgetResponseEngine(self.organization_id)

        result = engine.apply_custom_constraint(
            "987654321", "compute.vmExternalIpAccess", enforce=True, resource_type="folder"
        )

        # Should call get_policy and update_policy (upsert logic)
        self.assertTrue(mock_client.get_policy.called)
        self.assertTrue(mock_client.update_policy.called)
        self.assertTrue(result)

        # Verify correct parent format for folder
        update_call_args = mock_client.update_policy.call_args
        policy = update_call_args.kwargs["policy"]
        self.assertTrue(policy.name.startswith("folders/987654321/policies/"))

    @patch("budget_response_engine.PublisherClient")
    @patch("budget_response_engine.OrgPolicyClient")
    def test_event_publishing_includes_resource_type(
        self, mock_org_client_class, mock_pub_client_class
    ):
        """Test that published events include resource_type field."""
        mock_org_client = MagicMock()
        mock_org_client_class.return_value = mock_org_client

        mock_publisher = MagicMock()
        mock_future = MagicMock()
        mock_future.result.return_value = "msg-123"
        mock_publisher.publish.return_value = mock_future
        mock_pub_client_class.return_value = mock_publisher

        event_topic = "projects/test-project/topics/action-events"
        engine = BudgetResponseEngine(self.organization_id, event_topic=event_topic)

        result = engine.apply_service_restriction(
            "789456123", ["compute.googleapis.com"], action="deny", resource_type="folder"
        )

        # Should publish an event
        self.assertTrue(result)
        self.assertTrue(mock_publisher.publish.called)

        # Verify the published message structure includes resource_type
        call_args = mock_publisher.publish.call_args
        published_data = json.loads(call_args[0][1].decode("utf-8"))
        self.assertEqual(published_data["resource_id"], "789456123")
        self.assertEqual(published_data["resource_type"], "folder")
        self.assertEqual(published_data["action_type"], "restrict_services")

    def test_get_resource_parent_project(self):
        """Test get_resource_parent for project resources."""
        engine = BudgetResponseEngine(self.organization_id, dry_run=True)
        parent = engine.get_resource_parent("my-project-123", "project")
        self.assertEqual(parent, "projects/my-project-123")

    def test_get_resource_parent_folder(self):
        """Test get_resource_parent for folder resources."""
        engine = BudgetResponseEngine(self.organization_id, dry_run=True)
        parent = engine.get_resource_parent("123456789", "folder")
        self.assertEqual(parent, "folders/123456789")

    def test_get_resource_parent_organization(self):
        """Test get_resource_parent for organization resources."""
        engine = BudgetResponseEngine(self.organization_id, dry_run=True)
        parent = engine.get_resource_parent(self.organization_id, "organization")
        self.assertEqual(parent, f"organizations/{self.organization_id}")

    def test_get_resource_parent_invalid_type(self):
        """Test get_resource_parent with invalid resource type."""
        engine = BudgetResponseEngine(self.organization_id, dry_run=True)
        with self.assertRaises(ValueError):
            engine.get_resource_parent("123", "invalid_type")


if __name__ == "__main__":
    unittest.main()
