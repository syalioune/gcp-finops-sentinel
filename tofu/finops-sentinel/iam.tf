# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/google_service_account
# Service account for Cloud Run service
resource "google_service_account" "finops_sentinel" {
  project      = var.project_id
  account_id   = "finops-sentinel"
  display_name = "FinOps Sentinel Cloud Run Service Account"
  description  = "Service account for FinOps Sentinel to enforce organization policies based on budget alerts"
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/google_service_account_iam
# Grant Terraform service account permission to use (actAs) the FinOps Sentinel service account
resource "google_service_account_iam_member" "terraform_actas" {
  service_account_id = google_service_account.finops_sentinel.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${var.terraform_service_account}"
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/google_service_account
# Service account for Eventarc trigger
resource "google_service_account" "eventarc_trigger" {
  project      = var.project_id
  account_id   = "finops-sentinel-trigger"
  display_name = "FinOps Sentinel Eventarc Trigger Service Account"
  description  = "Service account for Eventarc trigger to invoke Cloud Run service"
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/google_service_account_iam
# Grant Terraform service account permission to use (actAs) the FinOps Sentinel trigger service account
resource "google_service_account_iam_member" "terraform_actas_trigger" {
  service_account_id = google_service_account.eventarc_trigger.name
  role               = "roles/iam.serviceAccountUser"
  member             = "serviceAccount:${var.terraform_service_account}"
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/google_organization_iam
# Grant Organization Policy Admin role at organization level
resource "google_organization_iam_member" "org_policy_admin" {
  org_id = var.organization_id
  role   = "roles/orgpolicy.policyAdmin"
  member = "serviceAccount:${google_service_account.finops_sentinel.email}"
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/google_organization_iam
# Grant Organization Viewer role for resource discovery
resource "google_organization_iam_member" "org_viewer" {
  org_id = var.organization_id
  role   = "roles/resourcemanager.organizationViewer"
  member = "serviceAccount:${google_service_account.finops_sentinel.email}"
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/google_organization_iam
# Grant Folder Viewer role for resource discovery
resource "google_organization_iam_member" "folder_viewer" {
  org_id = var.organization_id
  role   = "roles/resourcemanager.folderViewer"
  member = "serviceAccount:${google_service_account.finops_sentinel.email}"
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/google_project_iam
# Grant Service Usage Admin on target projects for service restrictions
resource "google_organization_iam_member" "service_usage_admin" {
  org_id = var.organization_id
  role   = "roles/serviceusage.serviceUsageAdmin"
  member = "serviceAccount:${google_service_account.finops_sentinel.email}"
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/google_project_iam
# Grant Compute Instance Admin for stopping instances (optional, based on use case)
resource "google_project_iam_member" "compute_instance_admin" {
  for_each = toset(var.target_projects)

  project = each.value
  role    = "roles/compute.instanceAdmin.v1"
  member  = "serviceAccount:${google_service_account.finops_sentinel.email}"
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/google_secret_manager_secret_iam
# Grant Secret Accessor role for reading rules configuration
resource "google_secret_manager_secret_iam_member" "rules_accessor" {
  secret_id = google_secret_manager_secret.rules_config.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.finops_sentinel.email}"
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/google_secret_manager_secret_iam
# Grant Secret Accessor role for reading SMTP password (only if SMTP is configured)
resource "google_secret_manager_secret_iam_member" "smtp_password_accessor" {
  count = var.smtp_password != null ? 1 : 0

  secret_id = google_secret_manager_secret.smtp_password[0].secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.finops_sentinel.email}"
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/google_pubsub_topic_iam
# Grant Pub/Sub Publisher role for action events (if enabled)
resource "google_pubsub_topic_iam_member" "action_event_publisher" {
  count = var.enable_action_events ? 1 : 0

  project = var.project_id
  topic   = google_pubsub_topic.action_events[0].name
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${google_service_account.finops_sentinel.email}"
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/google_project_iam
# Grant Cloud Run Invoker role to Eventarc trigger service account
resource "google_project_iam_member" "eventarc_trigger_invoker" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.eventarc_trigger.email}"
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/google_project_iam
# Grant Eventarc Event Receiver role
resource "google_project_iam_member" "eventarc_event_receiver" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.eventarc_trigger.email}"
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/google_project_iam
# Grant Pub/Sub Subscriber role to Eventarc trigger service account
resource "google_project_iam_member" "eventarc_pubsub_subscriber" {
  project = var.project_id
  role    = "roles/pubsub.subscriber"
  member  = "serviceAccount:${google_service_account.eventarc_trigger.email}"
}

# Grant Pub/Sub Token Creator for Eventarc (required for authenticated push)
resource "google_project_iam_member" "eventarc_token_creator" {
  project = var.project_id
  role    = "roles/iam.serviceAccountTokenCreator"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-pubsub.iam.gserviceaccount.com"
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/google_project_iam
# Grant Cloud Run Invoker role to Monitoring service agent for uptime checks
resource "google_project_iam_member" "monitoring_agent_invoker" {
  count = var.enable_monitoring ? 1 : 0

  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:service-${data.google_project.project.number}@gcp-sa-monitoring-notification.iam.gserviceaccount.com"
}
