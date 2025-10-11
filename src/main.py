"""
GCP FinOps Sentinel - Budget Response Cloud Function

This Cloud Function is triggered by Pub/Sub events from GCP Budget Alerts.
It enforces organization policies on projects based on configurable rules.

Main entry point that imports and exposes the handler function.
"""

import logging
import os

# Import and expose the handler function
from handler import budget_response_handler

# Configure logging
log_level = os.environ.get("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Export for Cloud Functions runtime
__all__ = ["budget_response_handler"]
