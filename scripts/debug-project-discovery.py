#!/usr/bin/env python3
"""
Debug script for testing project discovery by labels.

This script helps troubleshoot issues with label-based project discovery
by showing the exact query used and comparing with gcloud results.

Usage:
    # Test with specific labels
    python scripts/debug-project-discovery.py --labels env=prod team=backend

    # Test with organization ID
    python scripts/debug-project-discovery.py --labels env=prod --org 123456789012

    # Enable debug logging
    python scripts/debug-project-discovery.py --labels env=prod --debug

    # Compare with gcloud
    python scripts/debug-project-discovery.py --labels env=prod --compare-gcloud
"""

import argparse
import json
import logging
import os
import subprocess
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from project_discovery import ProjectDiscovery


def setup_logging(debug=False):
    """Setup logging configuration."""
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


def parse_labels(labels_str):
    """Parse label string into dictionary."""
    labels = {}
    for pair in labels_str:
        if "=" not in pair:
            raise ValueError(f"Invalid label format: {pair}. Expected key=value")
        key, value = pair.split("=", 1)
        labels[key] = value
    return labels


def compare_with_gcloud(labels, organization_id=None):
    """Compare results with gcloud command."""
    print("\n" + "=" * 70)
    print("Comparing with gcloud")
    print("=" * 70)

    # Build gcloud filter
    label_filters = [f"labels.{k}={v}" for k, v in labels.items()]
    filter_str = " AND ".join(label_filters)
    filter_str = f"({filter_str}) AND lifecycleState:ACTIVE"

    if organization_id:
        filter_str = f"parent.id={organization_id} AND {filter_str}"

    # Build gcloud command
    cmd = [
        "gcloud",
        "projects",
        "list",
        f"--filter={filter_str}",
        "--format=json",
    ]

    print(f"\nRunning gcloud command:")
    print(f"  {' '.join(cmd)}\n")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        projects = json.loads(result.stdout)

        print(f"✓ gcloud found {len(projects)} projects:")
        for project in projects:
            print(f"  - {project['projectId']} ({project['name']})")
            if "labels" in project:
                print(f"    Labels: {project['labels']}")

        return [p["projectId"] for p in projects]

    except subprocess.CalledProcessError as e:
        print(f"✗ gcloud command failed: {e}")
        print(f"  stderr: {e.stderr}")
        return None
    except FileNotFoundError:
        print("✗ gcloud command not found. Make sure Google Cloud SDK is installed.")
        return None
    except json.JSONDecodeError as e:
        print(f"✗ Failed to parse gcloud output: {e}")
        return None


def test_project_discovery(labels, organization_id=None, debug=False, compare=False):
    """Test project discovery with given labels."""
    print("\n" + "=" * 70)
    print("Testing Project Discovery")
    print("=" * 70)

    print(f"\nLabel filters: {labels}")
    if organization_id:
        print(f"Organization ID: {organization_id}")
    print(f"Debug logging: {debug}")

    # Initialize discovery service
    print("\nInitializing ProjectDiscovery...")
    discovery = ProjectDiscovery(dry_run=False)

    # Search for projects
    print("\nSearching for projects...")
    project_ids = discovery.find_projects_by_labels(labels, organization_id)

    # Display results
    print("\n" + "=" * 70)
    print(f"Results: Found {len(project_ids)} projects")
    print("=" * 70)

    if project_ids:
        print("\nProject IDs:")
        for pid in project_ids:
            print(f"  - {pid}")
    else:
        print("\n⚠️  No projects found!")
        print("\nTroubleshooting steps:")
        print("1. Verify labels exist on projects:")
        print(
            f"   gcloud projects list --filter='labels.{list(labels.keys())[0]}={list(labels.values())[0]}'"
        )
        print("\n2. Check if you have permission to search projects:")
        print("   Required: resourcemanager.projects.list")
        print("\n3. Verify organization ID (if specified):")
        if organization_id:
            print(f"   gcloud organizations list --filter='name:{organization_id}'")
        print("\n4. Enable debug logging to see the exact query:")
        print("   python scripts/debug-project-discovery.py --labels env=prod --debug")

    # Compare with gcloud if requested
    if compare:
        gcloud_projects = compare_with_gcloud(labels, organization_id)
        if gcloud_projects is not None:
            print("\n" + "=" * 70)
            print("Comparison Results")
            print("=" * 70)

            api_set = set(project_ids)
            gcloud_set = set(gcloud_projects)

            if api_set == gcloud_set:
                print("\n✓ Results match! API and gcloud found the same projects.")
            else:
                print("\n✗ Results differ!")
                only_api = api_set - gcloud_set
                only_gcloud = gcloud_set - api_set

                if only_api:
                    print(f"\nProjects found by API but not gcloud ({len(only_api)}):")
                    for pid in only_api:
                        print(f"  - {pid}")

                if only_gcloud:
                    print(f"\nProjects found by gcloud but not API ({len(only_gcloud)}):")
                    for pid in only_gcloud:
                        print(f"  - {pid}")

    return project_ids


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Debug project discovery by labels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test with single label
  python scripts/debug-project-discovery.py --labels env=prod

  # Test with multiple labels
  python scripts/debug-project-discovery.py --labels env=prod team=backend

  # Test with organization scope
  python scripts/debug-project-discovery.py --labels env=prod --org 123456789012

  # Compare with gcloud
  python scripts/debug-project-discovery.py --labels env=prod --compare-gcloud

  # Enable debug logging
  python scripts/debug-project-discovery.py --labels env=prod --debug
        """,
    )

    parser.add_argument(
        "--labels",
        nargs="+",
        required=True,
        metavar="KEY=VALUE",
        help="Label filters in key=value format",
    )
    parser.add_argument(
        "--org",
        "--organization",
        dest="organization_id",
        help="Organization ID to scope search",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--compare-gcloud",
        action="store_true",
        help="Compare results with gcloud command",
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.debug)

    try:
        # Parse labels
        labels = parse_labels(args.labels)

        # Test project discovery
        project_ids = test_project_discovery(
            labels,
            args.organization_id,
            args.debug,
            args.compare_gcloud,
        )

        # Exit with appropriate code
        sys.exit(0 if project_ids else 1)

    except ValueError as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(3)


if __name__ == "__main__":
    main()
