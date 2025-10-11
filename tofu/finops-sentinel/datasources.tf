# https://registry.terraform.io/providers/hashicorp/google/latest/docs/data-sources/project
# Get project data for service account references
data "google_project" "project" {
  project_id = var.project_id
}
