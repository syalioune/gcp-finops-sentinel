"""
Rule Engine - Evaluates budget alerts against configured rules.
"""

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class RuleEngine:
    """Engine for evaluating budget alert rules and determining actions."""

    def __init__(self, rules_config: Dict[str, Any]):
        """
        Initialize the rule engine.

        Args:
            rules_config: Configuration dictionary defining rules
        """
        self.rules = rules_config.get("rules", [])

    def evaluate(
        self, budget_data: Dict[str, Any], attributes: Optional[Dict[str, str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluate budget data against configured rules.

        Args:
            budget_data: Budget alert data from Pub/Sub message body
            attributes: Pub/Sub message attributes (contains billingAccountId, budgetId)

        Returns:
            List of actions to take
        """
        actions = []
        attributes = attributes or {}

        # Extract budget information
        cost_amount = budget_data.get("costAmount", 0)
        budget_amount = budget_data.get("budgetAmount", 0)
        threshold_percent = (
            round((cost_amount / budget_amount * 100), 1) if budget_amount > 0 else 0
        )

        billing_account_id = attributes.get("billingAccountId", "unknown")
        budget_id = attributes.get("budgetId", "unknown")

        logger.info(
            "Evaluating rules for billing account %s, "
            "budget %s: "
            "cost=%s, budget=%s, "
            "threshold=%.2f",
            billing_account_id,
            budget_id,
            cost_amount,
            budget_amount,
            threshold_percent,
        )

        # Evaluate each rule
        for rule in self.rules:
            if self._matches_rule(rule, threshold_percent, billing_account_id, budget_id):
                actions.extend(self._get_rule_actions(rule))

        return actions

    def _matches_rule(
        self,
        rule: Dict[str, Any],
        threshold_percent: float,
        billing_account_id: str,
        budget_id: str,
    ) -> bool:
        """Check if budget data matches a rule's conditions."""
        conditions = rule.get("conditions", {})

        # Check threshold - supports operators: >=, >, ==, <, <=, min, max
        # Can be a single condition dict or a list of conditions (all must match)
        threshold_condition = conditions.get("threshold_percent")
        if threshold_condition:
            # Support both single condition and array of conditions
            conditions_list = (
                threshold_condition
                if isinstance(threshold_condition, list)
                else [threshold_condition]
            )

            for cond in conditions_list:
                operator = cond.get("operator", ">=")
                value = cond.get("value", 100)

                if operator == ">=" and threshold_percent < value:
                    return False
                elif operator == ">" and threshold_percent <= value:
                    return False
                elif operator == "==" and threshold_percent != value:
                    return False
                elif operator == "<" and threshold_percent >= value:
                    return False
                elif operator == "<=" and threshold_percent > value:
                    return False
                elif operator == "min" and threshold_percent < value:
                    # "min" operator: threshold must be >= value (inclusive lower bound)
                    return False
                elif operator == "max" and threshold_percent > value:
                    # "max" operator: threshold must be <= value (inclusive upper bound)
                    return False

        # Check billing account filter
        billing_account_filter = conditions.get("billing_account_filter")
        if billing_account_filter:
            if isinstance(billing_account_filter, list):
                if billing_account_id not in billing_account_filter:
                    return False
            elif isinstance(billing_account_filter, dict):
                pattern = billing_account_filter.get("pattern")
                if pattern and not self._matches_pattern(billing_account_id, pattern):
                    return False
            elif isinstance(billing_account_filter, str):
                if billing_account_id != billing_account_filter:
                    return False

        # Check budget ID filter
        budget_id_filter = conditions.get("budget_id_filter")
        if budget_id_filter:
            if isinstance(budget_id_filter, list):
                if budget_id not in budget_id_filter:
                    return False
            elif isinstance(budget_id_filter, dict):
                pattern = budget_id_filter.get("pattern")
                if pattern and not self._matches_pattern(budget_id, pattern):
                    return False
            elif isinstance(budget_id_filter, str):
                if budget_id != budget_id_filter:
                    return False

        return True

    def _matches_pattern(self, text: str, pattern: str) -> bool:
        """Simple pattern matching (supports * wildcard)."""
        regex_pattern = pattern.replace("*", ".*")
        return bool(re.match(f"^{regex_pattern}$", text))

    def _get_rule_actions(self, rule: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Get actions defined in a rule.

        Actions can target resources in multiple ways:
        - target_projects: List of specific project IDs
        - target_folders: List of specific folder IDs
        - target_organization: Organization ID
        - target_labels: Dictionary of labels to filter projects by

        Some actions (like send_mail) don't require resource targeting.
        At least one targeting method must be specified for resource-based actions.
        """
        actions = []
        # Actions that don't require resource targeting
        non_resource_actions = {"send_mail"}

        for action in rule.get("actions", []):
            action_copy = action.copy()
            action_type = action_copy.get("type")

            # Skip target validation for actions that don't need resources
            if action_type in non_resource_actions:
                actions.append(action_copy)
                continue

            # Check if resource-based action has at least one targeting method
            has_targets = any(
                [
                    "target_projects" in action_copy,
                    "target_folders" in action_copy,
                    "target_organization" in action_copy,
                    "target_labels" in action_copy,
                ]
            )

            if not has_targets:
                logger.warning(
                    "Action %s in rule %s missing targeting specification "
                    "(target_projects, target_folders, target_organization, or target_labels) - skipping",
                    action_type,
                    rule.get("name"),
                )
                continue

            actions.append(action_copy)

        return actions
