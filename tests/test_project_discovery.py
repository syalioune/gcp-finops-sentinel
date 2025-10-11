"""
Unit tests for Project Discovery
"""

import unittest
from unittest.mock import MagicMock, patch

from project_discovery import ProjectDiscovery


class TestProjectDiscovery(unittest.TestCase):
    """Test cases for the ProjectDiscovery class."""

    def setUp(self):
        """Set up test fixtures."""
        self.organization_id = "123456789012"

    def test_dry_run_mode_initialization(self):
        """Test initialization in dry-run mode."""
        discovery = ProjectDiscovery(dry_run=True)
        self.assertIsNone(discovery.projects_client)
        self.assertTrue(discovery.dry_run)

    @patch("project_discovery.ProjectsClient")
    def test_real_mode_initialization(self, mock_client_class):
        """Test initialization in real mode."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        discovery = ProjectDiscovery(dry_run=False)
        self.assertIsNotNone(discovery.projects_client)
        self.assertFalse(discovery.dry_run)

    def test_find_projects_by_labels_dry_run(self):
        """Test finding projects by labels in dry-run mode."""
        discovery = ProjectDiscovery(dry_run=True)

        label_filters = {"env": "prod", "team": "backend"}
        projects = discovery.find_projects_by_labels(label_filters, self.organization_id)

        # Should return mock project IDs
        self.assertIsInstance(projects, list)
        self.assertEqual(len(projects), 2)
        self.assertIn("mock-project-env-prod", projects)
        self.assertIn("mock-project-team-backend", projects)

    @patch("project_discovery.ProjectsClient")
    def test_find_projects_by_labels_real_mode(self, mock_client_class):
        """Test finding projects by labels in real mode."""
        # Mock the projects client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Create mock project objects
        mock_project1 = MagicMock()
        mock_project1.name = "projects/prod-web-1"
        mock_project1.labels = {"env": "prod"}
        mock_project2 = MagicMock()
        mock_project2.name = "projects/prod-api-1"
        mock_project2.labels = {"env": "prod"}

        # Mock the search_projects response
        mock_client.search_projects.return_value = [mock_project1, mock_project2]

        discovery = ProjectDiscovery(dry_run=False)

        label_filters = {"env": "prod"}
        projects = discovery.find_projects_by_labels(label_filters, self.organization_id)

        # Verify the search was called
        self.assertTrue(mock_client.search_projects.called)

        # Verify returned project IDs
        self.assertEqual(len(projects), 2)
        self.assertIn("prod-web-1", projects)
        self.assertIn("prod-api-1", projects)

    @patch("project_discovery.ProjectsClient")
    def test_find_projects_by_multiple_labels(self, mock_client_class):
        """Test finding projects by multiple label filters."""
        # Mock the projects client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Create mock project objects
        mock_project1 = MagicMock()
        mock_project1.name = "projects/prod-backend-api"
        mock_project1.labels = {"env": "prod", "team": "backend"}

        mock_project2 = MagicMock()
        mock_project2.name = "projects/prod-frontend-api"
        mock_project2.labels = {"env": "prod", "team": "frontend"}

        # Mock the search_projects response
        mock_client.search_projects.return_value = [mock_project1, mock_project2]

        discovery = ProjectDiscovery(dry_run=False)

        label_filters = {"env": "prod", "team": "backend"}
        projects = discovery.find_projects_by_labels(label_filters, self.organization_id)

        # Verify the search was called
        self.assertTrue(mock_client.search_projects.called)

        # Verify returned project ID
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0], "prod-backend-api")

    @patch("project_discovery.ProjectsClient")
    def test_find_projects_without_organization_filter(self, mock_client_class):
        """Test finding projects without organization ID filter."""
        # Mock the projects client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Create mock project object
        mock_project = MagicMock()
        mock_project.name = "projects/test-project"
        mock_project.labels = {"env": "test"}

        # Mock the search_projects response
        mock_client.search_projects.return_value = [mock_project]

        discovery = ProjectDiscovery(dry_run=False)

        label_filters = {"env": "test"}
        projects = discovery.find_projects_by_labels(label_filters)

        # Verify the search was called
        self.assertTrue(mock_client.search_projects.called)

        # Verify returned project ID
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0], "test-project")

    @patch("project_discovery.ProjectsClient")
    def test_find_projects_error_handling(self, mock_client_class):
        """Test error handling when search fails."""
        # Mock the projects client
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # Mock search_projects to raise an exception
        mock_client.search_projects.side_effect = Exception("API Error")

        discovery = ProjectDiscovery(dry_run=False)

        label_filters = {"env": "prod"}
        projects = discovery.find_projects_by_labels(label_filters, self.organization_id)

        # Should return empty list on error
        self.assertEqual(len(projects), 0)


if __name__ == "__main__":
    unittest.main()
