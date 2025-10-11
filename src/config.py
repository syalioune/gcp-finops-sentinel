"""
Configuration utilities for loading rules and settings.
"""

import json
import logging
import os
from typing import Any, Dict

import yaml

logger = logging.getLogger(__name__)


def load_rules_config() -> Dict[str, Any]:
    """Load rules configuration from environment or file.

    Supports both JSON and YAML formats. When loading from environment variable,
    tries to parse as JSON first, then falls back to YAML. When loading from file,
    the format is determined by the file extension (.json, .yml, .yaml).
    """
    # Try to load from environment variable (JSON or YAML)
    rules_config_str = os.environ.get("RULES_CONFIG")
    if rules_config_str:
        # Try JSON first
        try:
            return json.loads(rules_config_str)
        except json.JSONDecodeError:
            # Fall back to YAML
            try:
                return yaml.safe_load(rules_config_str)
            except yaml.YAMLError as e:
                logger.error("Failed to parse RULES_CONFIG as JSON or YAML: %s", e)

    # Try to load from file (JSON or YAML)
    config_path = os.environ.get("RULES_CONFIG_PATH", "/workspace/rules.json")
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            # Determine format based on file extension
            if config_path.endswith((".yml", ".yaml")):
                return yaml.safe_load(f)
            else:
                return json.load(f)
    except FileNotFoundError:
        logger.warning("Rules config file not found: %s", config_path)
    except (json.JSONDecodeError, yaml.YAMLError) as e:
        logger.error("Failed to parse rules config file: %s", e)

    # Return default empty config
    return {"rules": []}
