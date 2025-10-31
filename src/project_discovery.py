"""
Project Discovery - Find projects based on label filters.
"""

import logging
from typing import Dict, List, Optional

from google.cloud.resourcemanager_v3 import ProjectsClient
from google.cloud.resourcemanager_v3.types import SearchProjectsRequest

logger = logging.getLogger(__name__)


class ProjectDiscovery:
    """Service for discovering projects based on label filters."""

    def __init__(self, dry_run: bool = False):
        """
        Initialize the project discovery service.

        Args:
            dry_run: If True, use mock data instead of real API calls
        """
        self.dry_run = dry_run

        if self.dry_run:
            logger.info("DRY-RUN MODE: Using mock project discovery")
            self.projects_client = None
        else:
            self.projects_client = ProjectsClient()
            logger.info("Initialized with real ProjectsClient")

    def find_projects_by_labels(
        self, label_filters: Dict[str, str], organization_id: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Find projects matching the given label filters.

        Args:
            label_filters: Dictionary of label key-value pairs to filter by
                          Example: {"env": "prod", "team": "backend"}
            organization_id: Optional organization ID to scope search

        Returns:
            List of dictionaries with project_id and display_name keys
            Example: [{"project_id": "my-project-123", "display_name": "My Project"}]
        """
        if self.dry_run:
            # Return mock project data for testing
            logger.info(
                "DRY-RUN: Would search for projects with labels %s in organization %s",
                label_filters,
                organization_id,
            )
            # Generate mock project data based on labels
            mock_projects = [
                {
                    "project_id": f"mock-project-{key}-{value}",
                    "display_name": f"Mock Project {key.title()} {value.title()}",
                }
                for key, value in label_filters.items()
            ]
            logger.info("DRY-RUN: Found mock projects: %s", mock_projects)
            return mock_projects

        try:
            # Build query string for label filtering
            # Format: labels.key:value (using colon, not equals)
            # WARNING: Multiple label conditions use OR logic, not AND
            # To match ALL labels, we filter results in post-processing
            label_queries = [f"labels.{key}:{value}" for key, value in label_filters.items()]

            # Combine with spaces (OR logic in API)
            label_query = " ".join(label_queries)

            # Build base query with state filter (only ACTIVE projects)
            query_parts = ["state:ACTIVE"]

            # Add organization filter if provided
            # Format: parent:organizations/ORGANIZATION_ID
            if organization_id:
                query_parts.append(f"parent:organizations/{organization_id}")

            # Add label query
            if label_query:
                query_parts.append(label_query)

            # Join all parts with spaces (each condition is applied)
            query = " ".join(query_parts)

            logger.info("Searching projects with query: %s", query)
            logger.debug(
                "Note: Label conditions use OR logic - will filter to AND in post-processing"
            )

            # Search for projects
            request = SearchProjectsRequest(query=query)
            projects = self.projects_client.search_projects(request=request)

            # Extract project data and filter to match ALL labels (AND logic)
            # The API uses OR logic for multiple labels, so we need to post-filter
            project_data = []
            for project in projects:
                # Check if project has all required labels with matching values
                if hasattr(project, "labels"):
                    project_labels = dict(project.labels) if project.labels else {}

                    # Check if all required label filters match
                    all_labels_match = all(
                        project_labels.get(key) == value for key, value in label_filters.items()
                    )

                    if all_labels_match:
                        # Extract project ID from project name (format: projects/PROJECT_ID)
                        project_id = project.name.split("/")[-1]
                        display_name = (
                            project.display_name if hasattr(project, "display_name") else project_id
                        )
                        project_data.append(
                            {"project_id": project_id, "display_name": display_name}
                        )
                        logger.debug(
                            "Matched project: %s (name: %s, labels: %s)",
                            project_id,
                            display_name,
                            project_labels,
                        )
                    else:
                        logger.debug(
                            "Skipping project %s: labels %s don't match all filters %s",
                            project.name,
                            project_labels,
                            label_filters,
                        )
                else:
                    logger.debug("Skipping project %s: no labels attribute", project.name)

            logger.info(
                "Found %d projects matching ALL labels %s: %s",
                len(project_data),
                label_filters,
                [p["project_id"] for p in project_data],
            )
            return project_data

        except Exception as e:
            logger.error(
                "Failed to search projects by labels %s: %s",
                label_filters,
                e,
                exc_info=True,
            )
            return []
