"""
Unit tests for configuration loading
"""

import json
import os
import unittest
from unittest.mock import mock_open, patch

import yaml

from config import load_rules_config


class TestLoadRulesConfig(unittest.TestCase):
    """Test cases for load_rules_config function."""

    @patch.dict("os.environ", {"RULES_CONFIG": json.dumps({"rules": [{"name": "test"}]})})
    def test_load_from_env_variable_json(self):
        """Test loading rules from environment variable (JSON format)."""
        config = load_rules_config()

        self.assertIn("rules", config)
        self.assertEqual(len(config["rules"]), 1)
        self.assertEqual(config["rules"][0]["name"], "test")

    @patch.dict(
        "os.environ",
        {"RULES_CONFIG": "rules:\n  - name: yaml_env_rule\n    description: Test YAML from env\n"},
    )
    def test_load_from_env_variable_yaml(self):
        """Test loading rules from environment variable (YAML format)."""
        config = load_rules_config()

        self.assertIn("rules", config)
        self.assertEqual(len(config["rules"]), 1)
        self.assertEqual(config["rules"][0]["name"], "yaml_env_rule")

    @patch.dict("os.environ", {"RULES_CONFIG": "invalid: yaml: content:"})
    def test_load_from_env_invalid_format(self):
        """Test loading invalid format from environment (neither valid JSON nor YAML)."""
        config = load_rules_config()

        # Should return default empty config
        self.assertEqual(config, {"rules": []})

    @patch.dict("os.environ", {}, clear=True)
    @patch("builtins.open", side_effect=FileNotFoundError())
    def test_load_file_not_found(self, mock_open):
        """Test loading when file not found."""
        config = load_rules_config()

        # Should return default empty config
        self.assertEqual(config, {"rules": []})

    @patch.dict("os.environ", {}, clear=True)
    @patch(
        "builtins.open",
        unittest.mock.mock_open(read_data='{"rules": [{"name": "file_rule"}]}'),
    )
    def test_load_from_file(self):
        """Test loading rules from file."""
        config = load_rules_config()

        self.assertIn("rules", config)

    @patch.dict("os.environ", {"RULES_CONFIG_PATH": "/workspace/rules.yaml"}, clear=True)
    @patch(
        "builtins.open",
        unittest.mock.mock_open(
            read_data="rules:\n  - name: yaml_rule\n    description: Test YAML rule\n"
        ),
    )
    def test_load_from_yaml_file(self):
        """Test loading rules from YAML file."""
        config = load_rules_config()

        self.assertIn("rules", config)
        self.assertEqual(len(config["rules"]), 1)
        self.assertEqual(config["rules"][0]["name"], "yaml_rule")

    @patch.dict("os.environ", {"RULES_CONFIG_PATH": "/workspace/rules.yml"}, clear=True)
    @patch(
        "builtins.open",
        unittest.mock.mock_open(
            read_data="rules:\n  - name: yml_rule\n    description: Test YML rule\n"
        ),
    )
    def test_load_from_yml_file(self):
        """Test loading rules from YML file (alternate extension)."""
        config = load_rules_config()

        self.assertIn("rules", config)
        self.assertEqual(len(config["rules"]), 1)
        self.assertEqual(config["rules"][0]["name"], "yml_rule")

    @patch.dict("os.environ", {"RULES_CONFIG_PATH": "/workspace/rules.yaml"}, clear=True)
    @patch("builtins.open", unittest.mock.mock_open(read_data="invalid: yaml: content:"))
    def test_load_from_yaml_invalid_syntax(self):
        """Test loading invalid YAML from file."""
        config = load_rules_config()

        # Should return default empty config
        self.assertEqual(config, {"rules": []})


if __name__ == "__main__":
    unittest.main()
