# FinOps Sentinel for automated budget enforcement
module "finops_sentinel" {
  source = "./finops-sentinel"

  project_id                = var.project_id
  terraform_service_account = var.terraform_service_account
  organization_id           = var.organization_id
  region                    = var.default_region

  # Container image from Artifact Registry
  container_image = var.container_image

  # Budget alert topic from budgets module
  budget_alert_topic_id = var.budget_alert_topic_id

  # Enable action events for observability
  enable_action_events = var.finops_enable_action_events

  # Dry run mode for testing
  dry_run = var.finops_dry_run

  # Rules configuration
  rules_config = var.finops_rules_config

  # SMTP configuration for email actions
  smtp_host       = var.smtp_host
  smtp_port       = var.smtp_port
  smtp_starttls   = var.smtp_starttls
  smtp_from_email = var.smtp_from_email
  smtp_user       = var.smtp_user
  smtp_password   = var.smtp_password

  # Monitoring alerts target email addresses
  enable_monitoring     = true
  alert_email_addresses = [var.budget_alert_email]

  labels = {
    environment = "landing-zone"
    team        = "platform"
  }
}