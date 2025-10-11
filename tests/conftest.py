"""
Pytest configuration and fixtures for GCP FinOps Sentinel tests.
"""

import sys
from pathlib import Path

# Add src directory to Python path so tests can import modules
src_dir = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_dir))
