# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/cloud_run_v2_service
# Cloud Run service for FinOps Sentinel
resource "google_cloud_run_v2_service" "finops_sentinel" {
  project  = var.project_id
  name     = var.service_name
  location = var.region

  template {
    service_account = google_service_account.finops_sentinel.email

    containers {
      image = var.container_image

      env {
        name  = "ORGANIZATION_ID"
        value = var.organization_id
      }

      env {
        name  = "RULES_CONFIG_PATH"
        value = "/secrets/rules.json"
      }

      env {
        name  = "LOG_LEVEL"
        value = var.log_level
      }

      env {
        name  = "DRY_RUN"
        value = var.dry_run ? "true" : "false"
      }

      # Optional: Action event topic for observability
      dynamic "env" {
        for_each = local.action_event_topic_id != "" ? toset(["1"]) : toset([])
        content {
          name  = "ACTION_EVENT_TOPIC"
          value = local.action_event_topic_id
        }
      }

      # Optional: SMTP configuration
      dynamic "env" {
        for_each = var.smtp_host != null ? toset(["1"]) : toset([])
        content {
          name  = "SMTP_HOST"
          value = var.smtp_host
        }
      }

      dynamic "env" {
        for_each = var.smtp_port != null ? toset(["1"]) : toset([])
        content {
          name  = "SMTP_PORT"
          value = tostring(var.smtp_port)
        }
      }

      dynamic "env" {
        for_each = var.smtp_starttls != null ? toset(["1"]) : toset([])
        content {
          name  = "SMTP_USE_TLS"
          value = var.smtp_starttls
        }
      }

      dynamic "env" {
        for_each = var.smtp_from_email != null ? toset(["1"]) : toset([])
        content {
          name  = "SMTP_FROM_EMAIL"
          value = var.smtp_from_email
        }
      }

      dynamic "env" {
        for_each = var.smtp_user != null ? toset(["1"]) : toset([])
        content {
          name  = "SMTP_USER"
          value = var.smtp_user
        }
      }

      # SMTP password from Secret Manager
      dynamic "env" {
        for_each = var.smtp_password != null ? toset(["1"]) : toset([])
        content {
          name = "SMTP_PASSWORD"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.smtp_password[0].secret_id
              version = "latest"
            }
          }
        }
      }

      # Mount rules configuration from Secret Manager
      volume_mounts {
        name       = "rules-config"
        mount_path = "/secrets"
      }

      resources {
        limits = {
          cpu    = var.cpu_limit
          memory = var.memory_limit
        }
      }
    }

    volumes {
      name = "rules-config"
      secret {
        secret = google_secret_manager_secret.rules_config.secret_id
        items {
          version = "latest"
          path    = "rules.json"
        }
      }
    }

    timeout = "${var.timeout_seconds}s"

    scaling {
      max_instance_count = var.max_instances
      min_instance_count = var.min_instances
    }

  }

  labels = merge(
    {
      purpose    = "finops-sentinel"
      managed_by = "terraform"
    },
    var.labels
  )

  depends_on = [
    google_project_service.required_apis,
    google_secret_manager_secret_version.rules_config_version
  ]
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/eventarc_trigger
# Eventarc trigger to connect Pub/Sub budget alerts to Cloud Run
resource "google_eventarc_trigger" "budget_alert_trigger" {
  project  = var.project_id
  name     = "${var.service_name}-trigger"
  location = var.region

  matching_criteria {
    attribute = "type"
    value     = "google.cloud.pubsub.topic.v1.messagePublished"
  }

  destination {
    cloud_run_service {
      service = google_cloud_run_v2_service.finops_sentinel.name
      region  = var.region
    }
  }

  transport {
    pubsub {
      topic = var.budget_alert_topic_id
    }
  }

  service_account = google_service_account.eventarc_trigger.email

  labels = merge(
    {
      purpose    = "budget-alert-trigger"
      managed_by = "terraform"
    },
    var.labels
  )

  depends_on = [
    google_cloud_run_v2_service.finops_sentinel,
    google_project_iam_member.eventarc_trigger_invoker,
    google_service_account_iam_member.terraform_actas_trigger
  ]
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/google_project_service
# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "run.googleapis.com",
    "eventarc.googleapis.com",
    "pubsub.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "orgpolicy.googleapis.com"
  ])

  project = var.project_id
  service = each.key

  disable_on_destroy = false
}
