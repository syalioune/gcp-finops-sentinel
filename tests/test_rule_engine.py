"""
Unit tests for RuleEngine
"""

import unittest

from rule_engine import RuleEngine


class TestRuleEngine(unittest.TestCase):
    """Test cases for the RuleEngine class."""

    def setUp(self):
        """Set up test fixtures."""
        self.rules_config = {
            "rules": [
                {
                    "name": "test_rule_100",
                    "description": "Test rule at 100%",
                    "conditions": {"threshold_percent": {"operator": ">=", "value": 100}},
                    "actions": [
                        {
                            "type": "restrict_services",
                            "target_projects": ["test-project-1"],
                            "services": ["compute.googleapis.com"],
                        }
                    ],
                },
                {
                    "name": "test_rule_50",
                    "description": "Test rule at 50% with billing account filter",
                    "conditions": {
                        "threshold_percent": {"operator": ">=", "value": 50},
                        "billing_account_filter": "012345-6789AB-CDEF01",
                    },
                    "actions": [
                        {
                            "type": "log_only",
                            "target_projects": ["test-project-1"],
                            "message": "Test message",
                        }
                    ],
                },
                {
                    "name": "test_rule_pattern",
                    "description": "Test rule with budget ID exact match",
                    "conditions": {
                        "threshold_percent": {"operator": ">=", "value": 75},
                        "budget_id_filter": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
                    },
                    "actions": [
                        {
                            "type": "apply_constraint",
                            "target_projects": ["dev-project-123"],
                            "constraint": "compute.vmExternalIpAccess",
                            "enforce": True,
                        }
                    ],
                },
            ]
        }
        self.engine = RuleEngine(self.rules_config)

    def test_evaluate_threshold_100_percent(self):
        """Test rule evaluation at 100% threshold."""
        budget_data = {
            "costAmount": 1000,
            "budgetAmount": 1000,
            "budgetDisplayName": "Test Budget",
        }
        attributes = {
            "billingAccountId": "999999-999999-999999",
            "budgetId": "test-budget",
        }

        actions = self.engine.evaluate(budget_data, attributes)

        # Should trigger rule with threshold >= 100%
        self.assertGreater(len(actions), 0)
        action_types = [a["type"] for a in actions]
        self.assertIn("restrict_services", action_types)

    def test_evaluate_threshold_60_percent(self):
        """Test rule evaluation at 60% threshold."""
        budget_data = {
            "costAmount": 600,
            "budgetAmount": 1000,
            "budgetDisplayName": "Test Budget",
        }
        attributes = {
            "billingAccountId": "012345-6789AB-CDEF01",
            "budgetId": "test-budget",
        }

        actions = self.engine.evaluate(budget_data, attributes)

        # Should trigger only rules with threshold <= 60%
        action_types = [a["type"] for a in actions]
        self.assertIn("log_only", action_types)
        self.assertNotIn("restrict_services", action_types)

    def test_evaluate_billing_account_filter_match(self):
        """Test billing account filter with exact match."""
        budget_data = {
            "costAmount": 600,
            "budgetAmount": 1000,
            "budgetDisplayName": "Test Budget",
        }
        attributes = {
            "billingAccountId": "012345-6789AB-CDEF01",
            "budgetId": "test-budget",
        }

        actions = self.engine.evaluate(budget_data, attributes)

        # Should match the rule with billing account filter
        self.assertTrue(any("test-project-1" in a.get("target_projects", []) for a in actions))

    def test_evaluate_budget_id_filter_match(self):
        """Test budget ID filter with UUID exact match."""
        budget_data = {
            "costAmount": 800,
            "budgetAmount": 1000,
            "budgetDisplayName": "Test Budget",
        }
        attributes = {
            "billingAccountId": "999999-999999-999999",
            "budgetId": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
        }

        actions = self.engine.evaluate(budget_data, attributes)

        # Should match the rule with exact UUID
        constraint_actions = [a for a in actions if a["type"] == "apply_constraint"]
        self.assertGreater(len(constraint_actions), 0)

    def test_evaluate_budget_id_filter_no_match(self):
        """Test budget ID filter that doesn't match."""
        budget_data = {
            "costAmount": 800,
            "budgetAmount": 1000,
            "budgetDisplayName": "Test Budget",
        }
        attributes = {
            "billingAccountId": "999999-999999-999999",
            "budgetId": "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d",
        }

        actions = self.engine.evaluate(budget_data, attributes)

        # Should not match the rule with different UUID
        constraint_actions = [a for a in actions if a["type"] == "apply_constraint"]
        self.assertEqual(len(constraint_actions), 0)

    def test_evaluate_no_match(self):
        """Test when no rules match."""
        budget_data = {
            "costAmount": 400,
            "budgetAmount": 1000,
            "budgetDisplayName": "Test Budget",
        }
        attributes = {
            "billingAccountId": "999999-999999-999999",
            "budgetId": "test-budget",
        }

        actions = self.engine.evaluate(budget_data, attributes)

        # No rules should match
        self.assertEqual(len(actions), 0)

    def test_matches_pattern(self):
        """Test pattern matching function."""
        self.assertTrue(self.engine._matches_pattern("dev-test-123", "dev-*"))
        self.assertTrue(self.engine._matches_pattern("test-dev-test", "*dev*"))
        self.assertFalse(self.engine._matches_pattern("prod-test", "dev-*"))

    def test_get_rule_actions(self):
        """Test action extraction from rules."""
        rule = self.rules_config["rules"][0]
        actions = self.engine._get_rule_actions(rule)

        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["type"], "restrict_services")
        self.assertEqual(actions[0]["target_projects"], ["test-project-1"])

    def test_missing_target_projects(self):
        """Test that actions without target_projects are skipped."""
        rules_config = {
            "rules": [
                {
                    "name": "test_rule_missing_target",
                    "conditions": {"threshold_percent": {"operator": ">=", "value": 50}},
                    "actions": [{"type": "log_only", "message": "Missing target_projects"}],
                }
            ]
        }
        engine = RuleEngine(rules_config)

        budget_data = {"costAmount": 600, "budgetAmount": 1000}
        actions = engine.evaluate(budget_data, {})

        # Action should be skipped due to missing target_projects
        self.assertEqual(len(actions), 0)

    def test_send_mail_action_without_targets(self):
        """Test that send_mail actions are NOT filtered out when they lack target resources."""
        rules_config = {
            "rules": [
                {
                    "name": "test_rule_send_mail",
                    "conditions": {"threshold_percent": {"operator": ">=", "value": 50}},
                    "actions": [
                        {
                            "type": "send_mail",
                            "to_emails": ["admin@example.com"],
                            "template": "budget_alert",
                        }
                    ],
                }
            ]
        }
        engine = RuleEngine(rules_config)

        budget_data = {"costAmount": 600, "budgetAmount": 1000}
        actions = engine.evaluate(budget_data, {})

        # send_mail action should NOT be skipped even without target resources
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["type"], "send_mail")
        self.assertEqual(actions[0]["to_emails"], ["admin@example.com"])

    def test_mixed_actions_with_and_without_targets(self):
        """Test that send_mail and resource-based actions work together."""
        rules_config = {
            "rules": [
                {
                    "name": "test_rule_mixed",
                    "conditions": {"threshold_percent": {"operator": ">=", "value": 80}},
                    "actions": [
                        {
                            "type": "restrict_services",
                            "target_projects": ["prod-project"],
                            "services": ["compute.googleapis.com"],
                        },
                        {
                            "type": "send_mail",
                            "to_emails": ["sre@example.com"],
                            "template": "budget_alert",
                        },
                        {
                            "type": "log_only",
                            # Missing target - should be filtered out
                            "message": "No target",
                        },
                    ],
                }
            ]
        }
        engine = RuleEngine(rules_config)

        budget_data = {"costAmount": 900, "budgetAmount": 1000}
        actions = engine.evaluate(budget_data, {})

        # Should have 2 actions: restrict_services and send_mail (log_only filtered out)
        self.assertEqual(len(actions), 2)
        action_types = [a["type"] for a in actions]
        self.assertIn("restrict_services", action_types)
        self.assertIn("send_mail", action_types)
        self.assertNotIn("log_only", action_types)

    def test_min_operator(self):
        """Test 'min' operator as threshold condition."""
        rules_config = {
            "rules": [
                {
                    "name": "min_operator_80",
                    "conditions": {"threshold_percent": {"operator": "min", "value": 80}},
                    "actions": [
                        {
                            "type": "log_only",
                            "target_projects": ["project-min-80"],
                            "message": "Min 80% reached",
                        }
                    ],
                }
            ]
        }
        engine = RuleEngine(rules_config)

        # Test 80% - should match (inclusive)
        budget_data = {"costAmount": 800, "budgetAmount": 1000}
        actions = engine.evaluate(budget_data, {})
        self.assertEqual(len(actions), 1)

        # Test 85% - should match
        budget_data = {"costAmount": 850, "budgetAmount": 1000}
        actions = engine.evaluate(budget_data, {})
        self.assertEqual(len(actions), 1)

        # Test 79.5% - should not match
        budget_data = {"costAmount": 795, "budgetAmount": 1000}
        actions = engine.evaluate(budget_data, {})
        self.assertEqual(len(actions), 0)

    def test_max_operator(self):
        """Test 'max' operator as threshold condition."""
        rules_config = {
            "rules": [
                {
                    "name": "max_operator_90",
                    "conditions": {"threshold_percent": {"operator": "max", "value": 90}},
                    "actions": [
                        {
                            "type": "log_only",
                            "target_projects": ["project-max-90"],
                            "message": "Max 90% threshold",
                        }
                    ],
                }
            ]
        }
        engine = RuleEngine(rules_config)

        # Test 90% - should match (inclusive)
        budget_data = {"costAmount": 900, "budgetAmount": 1000}
        actions = engine.evaluate(budget_data, {})
        self.assertEqual(len(actions), 1)

        # Test 85% - should match
        budget_data = {"costAmount": 850, "budgetAmount": 1000}
        actions = engine.evaluate(budget_data, {})
        self.assertEqual(len(actions), 1)

        # Test 95% - should not match
        budget_data = {"costAmount": 950, "budgetAmount": 1000}
        actions = engine.evaluate(budget_data, {})
        self.assertEqual(len(actions), 0)

    def test_min_max_operators_array(self):
        """Test array of 'min' and 'max' operators for range conditions."""
        rules_config = {
            "rules": [
                {
                    "name": "range_80_89_operators",
                    "conditions": {
                        "threshold_percent": [
                            {"operator": "min", "value": 80},
                            {"operator": "max", "value": 89.99},
                        ]
                    },
                    "actions": [
                        {
                            "type": "log_only",
                            "target_projects": ["project-80-89"],
                            "message": "80-89.99 range using operators",
                        }
                    ],
                },
                {
                    "name": "range_90_99_operators",
                    "conditions": {
                        "threshold_percent": [
                            {"operator": "min", "value": 90},
                            {"operator": "max", "value": 99.99},
                        ]
                    },
                    "actions": [
                        {
                            "type": "log_only",
                            "target_projects": ["project-90-99"],
                            "message": "90-99.99 range using operators",
                        }
                    ],
                },
            ]
        }
        engine = RuleEngine(rules_config)

        # Test 82% - should match first range only
        budget_data = {"costAmount": 820, "budgetAmount": 1000}
        actions = engine.evaluate(budget_data, {})
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["target_projects"], ["project-80-89"])

        # Test 95% - should match second range only
        budget_data = {"costAmount": 950, "budgetAmount": 1000}
        actions = engine.evaluate(budget_data, {})
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["target_projects"], ["project-90-99"])

        # Test 79% - should match neither (below both ranges)
        budget_data = {"costAmount": 790, "budgetAmount": 1000}
        actions = engine.evaluate(budget_data, {})
        self.assertEqual(len(actions), 0)

        # Test 100% - should match neither (above both ranges)
        budget_data = {"costAmount": 1000, "budgetAmount": 1000}
        actions = engine.evaluate(budget_data, {})
        self.assertEqual(len(actions), 0)

        # Test boundary 80% - should match first range (inclusive)
        budget_data = {"costAmount": 800, "budgetAmount": 1000}
        actions = engine.evaluate(budget_data, {})
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["target_projects"], ["project-80-89"])

        # Test boundary 89.9% - should match first range (inclusive)
        budget_data = {"costAmount": 899, "budgetAmount": 1000}
        actions = engine.evaluate(budget_data, {})
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0]["target_projects"], ["project-80-89"])

    def test_min_operator_only_open_ended(self):
        """Test 'min' operator without 'max' for open-ended range."""
        rules_config = {
            "rules": [
                {
                    "name": "min_only_115",
                    "conditions": {"threshold_percent": {"operator": "min", "value": 115}},
                    "actions": [
                        {
                            "type": "log_only",
                            "target_projects": ["project-115-plus"],
                            "message": "115+ using min operator",
                        }
                    ],
                }
            ]
        }
        engine = RuleEngine(rules_config)

        # Test 115% - should match
        budget_data = {"costAmount": 1150, "budgetAmount": 1000}
        actions = engine.evaluate(budget_data, {})
        self.assertEqual(len(actions), 1)

        # Test 200% - should match (no upper bound)
        budget_data = {"costAmount": 2000, "budgetAmount": 1000}
        actions = engine.evaluate(budget_data, {})
        self.assertEqual(len(actions), 1)

        # Test 114% - should not match
        budget_data = {"costAmount": 1140, "budgetAmount": 1000}
        actions = engine.evaluate(budget_data, {})
        self.assertEqual(len(actions), 0)


if __name__ == "__main__":
    unittest.main()
