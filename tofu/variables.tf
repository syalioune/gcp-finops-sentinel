variable "organization_id" {
  description = "GCP Organization ID"
  type        = string
  default     = "123456789012"
}

variable "billing_account_id" {
  description = "Billing Account ID"
  type        = string
}

variable "landing_zone_project_id" {
  description = "Landing zone project ID for Terraform state"
  type        = string
}

variable "landing_zone_project_number" {
  description = "Landing zone project number for Terraform state"
  type        = string
}

variable "terraform_service_account" {
  description = "Email of the Terraform service account executing the deployment"
  type        = string
}

variable "project_id" {
  description = "Project ID where FinOps Sentinel will be deployed"
  type        = string
}

variable "container_image" {
  description = "Container image URL in Artifact Registry (e.g., us-docker.pkg.dev/PROJECT/REPO/gcp-finops-sentinel:latest)"
  type        = string
}

variable "budget_alert_topic_id" {
  description = "Full Pub/Sub topic ID for budget alerts (e.g., projects/PROJECT_ID/topics/budget-alerts)"
  type        = string
}

variable "budget_alert_email" {
  description = "Email address to receive budget alert notifications and monitoring alerts"
  type        = string
}

variable "default_region" {
  description = "Default GCP region for deployment"
  type        = string
  default     = "us-central1"
}

variable "finops_enable_action_events" {
  description = "Enable action events Pub/Sub topic for FinOps Sentinel observability"
  type        = bool
  default     = true
}

variable "finops_dry_run" {
  description = "Enable dry-run mode for FinOps Sentinel (test without applying policies)"
  type        = bool
  default     = true
}

variable "finops_rules_config" {
  description = "FinOps Sentinel rules configuration as JSON string with progressive, non-overlapping thresholds"
  type        = string
  default     = <<-EOT
    {
      "rules": [
        {
          "name": "uptime_check_health_monitor",
          "description": "Log uptime check health requests without taking action",
          "conditions": {
            "threshold_percent": {"operator": ">=", "value": 0},
            "budget_id_filter": "uptime-check-budget-id",
            "billing_account_filter": "uptime-check-billing-account"
          },
          "actions": [
            {
              "type": "log_only",
              "message": "Health check received from monitoring uptime check - no action taken"
            }
          ]
        },
        {
          "name": "advisory_50_79_percent",
          "description": "Advisory threshold (50-79%) - Send email notification only",
          "conditions": {
            "threshold_percent": [
              {"operator": "min", "value": 50},
              {"operator": "max", "value": 79.99}
            ]
          },
          "actions": [
            {
              "type": "log_only",
              "target_projects": ["example-project-1"],
              "message": "ADVISORY: Budget at 50-79%. Monitor spending closely."
            },
            {
              "type": "send_mail",
              "to_emails": ["finops-team@example.com"],
              "template": "budget_alert",
              "custom_message": "Budget has reached 50-79%. Review spending trends."
            }
          ]
        },
        {
          "name": "warning_80_89_percent",
          "description": "Warning threshold (80-89%) - Restrict expensive compute services",
          "conditions": {
            "threshold_percent": [
              {"operator": "min", "value": 80},
              {"operator": "max", "value": 89.99}
            ]
          },
          "actions": [
            {
              "type": "log_only",
              "target_projects": ["example-project-1", "example-project-2"],
              "message": "WARNING: Budget at 80-89%. Restricting expensive services."
            },
            {
              "type": "restrict_services",
              "target_projects": ["example-project-1"],
              "services": ["compute.googleapis.com", "container.googleapis.com"]
            },
            {
              "type": "send_mail",
              "to_emails": ["finops-team@example.com", "engineering-leads@example.com"],
              "template": "budget_alert",
              "custom_message": "WARNING: Budget at 80-89%. Compute and GKE services restricted."
            }
          ]
        },
        {
          "name": "critical_90_99_percent",
          "description": "Critical threshold (90-99%) - Restrict most cloud services",
          "conditions": {
            "threshold_percent": [
              {"operator": "min", "value": 90},
              {"operator": "max", "value": 99.99}
            ]
          },
          "actions": [
            {
              "type": "restrict_services",
              "target_projects": ["example-project-1", "example-project-2"],
              "services": [
                "compute.googleapis.com",
                "run.googleapis.com",
                "cloudfunctions.googleapis.com",
                "container.googleapis.com",
                "dataflow.googleapis.com"
              ]
            },
            {
              "type": "send_mail",
              "to_emails": ["finops-team@example.com", "engineering-leads@example.com", "cto@example.com"],
              "template": "budget_alert",
              "custom_message": "CRITICAL: Budget at 90-99%. Major services restricted to prevent overrun."
            }
          ]
        },
        {
          "name": "emergency_100_percent_plus",
          "description": "Emergency threshold (100%+) - Restrict all non-essential services",
          "conditions": {
            "threshold_percent": {
              "operator": "min",
              "value": 100
            }
          },
          "actions": [
            {
              "type": "restrict_services",
              "target_projects": ["example-project-1", "example-project-2", "example-project-3"],
              "services": [
                "compute.googleapis.com",
                "run.googleapis.com",
                "cloudfunctions.googleapis.com",
                "container.googleapis.com",
                "dataflow.googleapis.com",
                "aiplatform.googleapis.com",
                "bigquery.googleapis.com"
              ]
            },
            {
              "type": "send_mail",
              "to_emails": ["finops-team@example.com", "engineering-leads@example.com", "cto@example.com", "cfo@example.com"],
              "template": "budget_alert",
              "custom_message": "EMERGENCY: Budget exceeded 100%. All non-essential services restricted immediately."
            }
          ]
        },
        {
          "name": "folder_targeting_80_percent",
          "description": "Apply policy to all projects in a folder at 80%",
          "conditions": {
            "threshold_percent": [
              {"operator": "min", "value": 80},
              {"operator": "max", "value": 89.99}
            ]
          },
          "actions": [
            {
              "target_folders": ["123456789012"],
              "type": "restrict_services",
              "services": ["compute.googleapis.com", "container.googleapis.com"]
            }
          ]
        },
        {
          "name": "label_based_dev_projects_90_percent",
          "description": "Target development projects by labels at 90%",
          "conditions": {
            "threshold_percent": [
              {"operator": "min", "value": 90},
              {"operator": "max", "value": 99.99}
            ]
          },
          "actions": [
            {
              "type": "restrict_services",
              "target_labels": {
                "environment": "dev",
                "cost-center": "engineering"
              },
              "services": [
                "run.googleapis.com",
                "cloudfunctions.googleapis.com",
                "aiplatform.googleapis.com"
              ]
            }
          ]
        }
      ]
    }
  EOT
}

variable "smtp_host" {
  description = "SMTP server host for sending email notifications (optional, required for send_mail actions)"
  type        = string
  default     = ""
}

variable "smtp_port" {
  description = "SMTP server port"
  type        = number
  default     = 587
}

variable "smtp_starttls" {
  description = "Enable STARTTLS for SMTP connection (true/false)"
  type        = string
  default     = "true"
}

variable "smtp_from_email" {
  description = "From email address for SMTP notifications"
  type        = string
  default     = ""
}

variable "smtp_user" {
  description = "SMTP username for authentication (optional)"
  type        = string
  default     = ""
}

variable "smtp_password" {
  description = "SMTP password for authentication (optional, stored in Secret Manager if provided)"
  type        = string
  sensitive   = true
  default     = ""
}