"""
Unit tests for budget response handler
"""

import base64
import json
import sys
import unittest
from unittest.mock import MagicMock, Mock, patch

# Mock functions_framework before importing handler
# Create a mock that makes the cloud_event decorator a no-op (passthrough)
mock_ff = MagicMock()
mock_ff.cloud_event = lambda func: func  # Decorator returns function unchanged
sys.modules["functions_framework"] = mock_ff

from handler import budget_response_handler


class TestBudgetResponseHandler(unittest.TestCase):
    """Test cases for the budget_response_handler function."""

    def setUp(self):
        """Set up test fixtures."""
        self.rules_config = {
            "rules": [
                {
                    "name": "test_rule",
                    "conditions": {"threshold_percent": {"operator": ">=", "value": 100}},
                    "actions": [{"type": "log_only", "message": "Test action"}],
                }
            ]
        }

    @patch.dict(
        "os.environ",
        {"ORGANIZATION_ID": "123456789012", "RULES_CONFIG": json.dumps({"rules": []})},
    )
    @patch("handler.load_rules_config")
    @patch("handler.BudgetResponseEngine")
    @patch("handler.RuleEngine")
    @patch("handler.ProjectDiscovery")
    def test_handler_success(
        self,
        mock_project_discovery_class,
        mock_rule_engine_class,
        mock_response_engine_class,
        mock_load_config,
    ):
        """Test successful handler execution."""
        # Create mock cloud event
        budget_data = {
            "costAmount": 1000,
            "budgetAmount": 1000,
            "budgetDisplayName": "Test Budget",
        }

        message_data = base64.b64encode(json.dumps(budget_data).encode())

        cloud_event = Mock()
        cloud_event.data = {"message": {"data": message_data, "attributes": {}}}

        # Mock config loading
        mock_load_config.return_value = {"rules": []}

        # Mock rule engine
        mock_rule_engine = MagicMock()
        mock_rule_engine.evaluate.return_value = [
            {"type": "log_only", "target_projects": ["test-project"], "message": "Test"}
        ]
        mock_rule_engine_class.return_value = mock_rule_engine

        # Mock response engine
        mock_response_engine = MagicMock()
        mock_response_engine_class.return_value = mock_response_engine

        # Mock project discovery
        mock_project_discovery = MagicMock()
        mock_project_discovery_class.return_value = mock_project_discovery

        # Call handler
        budget_response_handler(cloud_event)

        # Verify config was loaded
        mock_load_config.assert_called_once()

        # Verify rule engine was initialized and called with both budget_data and attributes
        mock_rule_engine_class.assert_called_once_with({"rules": []})
        mock_rule_engine.evaluate.assert_called_once_with(budget_data, {})

    @patch.dict("os.environ", {}, clear=True)
    def test_handler_missing_org_id(self):
        """Test handler with missing organization ID."""
        cloud_event = Mock()
        cloud_event.data = {
            "message": {"data": base64.b64encode(b'{"test": "data"}'), "attributes": {}}
        }

        # Should not raise exception, just log error
        budget_response_handler(cloud_event)

    @patch.dict("os.environ", {"ORGANIZATION_ID": "123456789012"})
    @patch("handler.load_rules_config")
    def test_handler_invalid_json(self, mock_load_config):
        """Test handler with invalid JSON."""
        mock_load_config.return_value = {"rules": []}

        cloud_event = Mock()
        cloud_event.data = {
            "message": {"data": base64.b64encode(b"invalid json"), "attributes": {}}
        }

        # Should raise exception due to invalid JSON
        with self.assertRaises(json.JSONDecodeError):
            budget_response_handler(cloud_event)

    @patch.dict(
        "os.environ",
        {"ORGANIZATION_ID": "123456789012", "RULES_CONFIG": json.dumps({"rules": []})},
    )
    @patch("handler.load_rules_config")
    @patch("handler.BudgetResponseEngine")
    @patch("handler.RuleEngine")
    @patch("handler.ProjectDiscovery")
    def test_handler_send_mail_action(
        self,
        mock_project_discovery_class,
        mock_rule_engine_class,
        mock_response_engine_class,
        mock_load_config,
    ):
        """Test handler with send_mail action."""
        # Create mock cloud event
        budget_data = {
            "costAmount": 1500,
            "budgetAmount": 1000,
            "budgetDisplayName": "Test Budget",
        }

        message_data = base64.b64encode(json.dumps(budget_data).encode())

        cloud_event = Mock()
        cloud_event.data = {
            "message": {
                "data": message_data,
                "attributes": {
                    "billingAccountId": "012345-ABCDEF-123456",
                    "budgetId": "budget-123",
                },
            }
        }

        # Mock config loading
        mock_load_config.return_value = {"rules": []}

        # Mock rule engine to return send_mail action
        mock_rule_engine = MagicMock()
        mock_rule_engine.evaluate.return_value = [
            {
                "type": "send_mail",
                "to_emails": ["admin@example.com", "finops@example.com"],
                "template": "budget_alert",
                "custom_message": "Critical budget threshold exceeded",
            }
        ]
        mock_rule_engine_class.return_value = mock_rule_engine

        # Mock response engine
        mock_response_engine = MagicMock()
        mock_response_engine.send_email.return_value = True
        mock_response_engine_class.return_value = mock_response_engine

        # Mock project discovery
        mock_project_discovery = MagicMock()
        mock_project_discovery_class.return_value = mock_project_discovery

        # Call handler
        budget_response_handler(cloud_event)

        # Verify send_email was called with correct parameters
        mock_response_engine.send_email.assert_called_once()
        call_args = mock_response_engine.send_email.call_args

        assert call_args.kwargs["to_emails"] == ["admin@example.com", "finops@example.com"]
        assert call_args.kwargs["template"] == "budget_alert"
        assert call_args.kwargs["custom_message"] == "Critical budget threshold exceeded"
        assert "budget_data" in call_args.kwargs
        assert call_args.kwargs["budget_data"]["cost_amount"] == 1500
        assert call_args.kwargs["budget_data"]["budget_amount"] == 1000
        assert call_args.kwargs["budget_data"]["threshold_percent"] == 150.0

    @patch.dict(
        "os.environ",
        {"ORGANIZATION_ID": "123456789012", "RULES_CONFIG": json.dumps({"rules": []})},
    )
    @patch("handler.load_rules_config")
    @patch("handler.BudgetResponseEngine")
    @patch("handler.RuleEngine")
    @patch("handler.ProjectDiscovery")
    def test_handler_send_mail_with_prior_actions(
        self,
        mock_project_discovery_class,
        mock_rule_engine_class,
        mock_response_engine_class,
        mock_load_config,
    ):
        """Test handler with send_mail action after other actions."""
        # Create mock cloud event
        budget_data = {
            "costAmount": 1200,
            "budgetAmount": 1000,
            "budgetDisplayName": "Test Budget",
        }

        message_data = base64.b64encode(json.dumps(budget_data).encode())

        cloud_event = Mock()
        cloud_event.data = {
            "message": {
                "data": message_data,
                "attributes": {
                    "billingAccountId": "012345-ABCDEF-123456",
                    "budgetId": "budget-123",
                },
            }
        }

        # Mock config loading
        mock_load_config.return_value = {"rules": []}

        # Mock rule engine to return multiple actions including send_mail
        mock_rule_engine = MagicMock()
        mock_rule_engine.evaluate.return_value = [
            {
                "type": "restrict_services",
                "target_projects": ["my-project"],
                "services": ["compute.googleapis.com"],
            },
            {
                "type": "log_only",
                "target_projects": ["my-project"],
                "message": "Budget exceeded",
            },
            {
                "type": "send_mail",
                "to_emails": ["admin@example.com"],
                "template": "budget_alert",
            },
        ]
        mock_rule_engine_class.return_value = mock_rule_engine

        # Mock response engine
        mock_response_engine = MagicMock()
        mock_response_engine.apply_service_restriction.return_value = True
        mock_response_engine.send_email.return_value = True
        mock_response_engine_class.return_value = mock_response_engine

        # Mock project discovery
        mock_project_discovery = MagicMock()
        mock_project_discovery_class.return_value = mock_project_discovery

        # Call handler
        budget_response_handler(cloud_event)

        # Verify actions were executed
        mock_response_engine.apply_service_restriction.assert_called_once()
        mock_response_engine.send_email.assert_called_once()

        # Verify send_email received executed_actions list
        call_args = mock_response_engine.send_email.call_args
        actions_taken = call_args.kwargs["actions_taken"]

        # Should have 2 prior actions (restrict_services and log_only)
        assert len(actions_taken) == 2
        assert actions_taken[0]["type"] == "restrict_services"
        assert actions_taken[1]["type"] == "log_only"

    @patch.dict(
        "os.environ",
        {"ORGANIZATION_ID": "123456789012", "RULES_CONFIG": json.dumps({"rules": []})},
    )
    @patch("handler.load_rules_config")
    @patch("handler.BudgetResponseEngine")
    @patch("handler.RuleEngine")
    @patch("handler.ProjectDiscovery")
    def test_handler_send_mail_missing_emails(
        self,
        mock_project_discovery_class,
        mock_rule_engine_class,
        mock_response_engine_class,
        mock_load_config,
    ):
        """Test handler with send_mail action missing to_emails."""
        # Create mock cloud event
        budget_data = {"costAmount": 1000, "budgetAmount": 1000}

        message_data = base64.b64encode(json.dumps(budget_data).encode())

        cloud_event = Mock()
        cloud_event.data = {"message": {"data": message_data, "attributes": {}}}

        # Mock config loading
        mock_load_config.return_value = {"rules": []}

        # Mock rule engine to return send_mail action without to_emails
        mock_rule_engine = MagicMock()
        mock_rule_engine.evaluate.return_value = [
            {
                "type": "send_mail",
                "template": "budget_alert",
            }
        ]
        mock_rule_engine_class.return_value = mock_rule_engine

        # Mock response engine
        mock_response_engine = MagicMock()
        mock_response_engine_class.return_value = mock_response_engine

        # Mock project discovery
        mock_project_discovery = MagicMock()
        mock_project_discovery_class.return_value = mock_project_discovery

        # Call handler - should skip the action without raising
        budget_response_handler(cloud_event)

        # Verify send_email was NOT called
        mock_response_engine.send_email.assert_not_called()


if __name__ == "__main__":
    unittest.main()
