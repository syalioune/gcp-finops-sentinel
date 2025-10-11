# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret
# Secret Manager secret for rules configuration
resource "google_secret_manager_secret" "rules_config" {
  project   = var.project_id
  secret_id = "${var.service_name}-rules"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  labels = merge(
    {
      purpose    = "finops-sentinel-rules"
      managed_by = "terraform"
    },
    var.labels
  )

  depends_on = [
    google_project_service.required_apis
  ]
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret_version
# Store rules configuration as secret version
resource "google_secret_manager_secret_version" "rules_config_version" {
  secret      = google_secret_manager_secret.rules_config.id
  secret_data = var.rules_config
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret
# Secret Manager secret for SMTP password (only created if smtp_password is provided)
resource "google_secret_manager_secret" "smtp_password" {
  count     = var.smtp_password != null ? 1 : 0
  project   = var.project_id
  secret_id = "${var.service_name}-smtp-password"

  replication {
    user_managed {
      replicas {
        location = var.region
      }
    }
  }

  labels = merge(
    {
      purpose    = "finops-sentinel-smtp"
      managed_by = "terraform"
    },
    var.labels
  )

  depends_on = [
    google_project_service.required_apis
  ]
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/secret_manager_secret_version
# Store SMTP password as secret version
resource "google_secret_manager_secret_version" "smtp_password_version" {
  count       = var.smtp_password != null ? 1 : 0
  secret      = google_secret_manager_secret.smtp_password[0].id
  secret_data = var.smtp_password
}
