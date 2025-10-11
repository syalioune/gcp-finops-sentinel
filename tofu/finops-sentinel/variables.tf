variable "project_id" {
  description = "GCP project ID where the Cloud Run service will be deployed"
  type        = string
}

variable "terraform_service_account" {
  description = "Email of the Terraform service account that needs actAs permission on the Cloud Run service account"
  type        = string
}

variable "organization_id" {
  description = "GCP Organization ID for policy enforcement"
  type        = string
}

variable "region" {
  description = "GCP region for Cloud Run deployment"
  type        = string
  default     = "europe-west9"
}

variable "service_name" {
  description = "Name of the Cloud Run service"
  type        = string
  default     = "gcp-finops-sentinel"
}

variable "container_image" {
  description = "Container image URL in Artifact Registry (e.g., europe-west9-docker.pkg.dev/PROJECT/REPO/IMAGE:TAG)"
  type        = string
}

variable "budget_alert_topic_id" {
  description = "Full Pub/Sub topic ID for budget alerts (e.g., projects/PROJECT/topics/budget-alerts)"
  type        = string
}

variable "enable_action_events" {
  description = "Enable creation of Pub/Sub topic for publishing policy action events"
  type        = bool
  default     = false
}

variable "rules_config" {
  description = "FinOps Sentinel rules configuration as JSON string"
  type        = string
}

variable "cpu_limit" {
  description = "CPU limit for Cloud Run service"
  type        = string
  default     = "1"
}

variable "memory_limit" {
  description = "Memory limit for Cloud Run service"
  type        = string
  default     = "512Mi"
}

variable "timeout_seconds" {
  description = "Request timeout for Cloud Run service in seconds"
  type        = number
  default     = 300
}

variable "max_instances" {
  description = "Maximum number of Cloud Run instances"
  type        = number
  default     = 10
}

variable "min_instances" {
  description = "Minimum number of Cloud Run instances"
  type        = number
  default     = 0
}

variable "log_level" {
  description = "Logging level (DEBUG, INFO, WARNING, ERROR)"
  type        = string
  default     = "INFO"

  validation {
    condition     = contains(["DEBUG", "INFO", "WARNING", "ERROR"], var.log_level)
    error_message = "Log level must be one of: DEBUG, INFO, WARNING, ERROR"
  }
}

variable "dry_run" {
  description = "Enable dry-run mode to test without applying policies"
  type        = bool
  default     = false
}

variable "labels" {
  description = "Additional labels to apply to resources"
  type        = map(string)
  default     = {}
}

# Monitoring variables
variable "enable_monitoring" {
  description = "Enable uptime checks and alert policies for the Cloud Run service"
  type        = bool
  default     = true
}

variable "health_check_path" {
  description = "Path for the uptime health check endpoint"
  type        = string
  default     = "/health"
}

variable "alert_email_addresses" {
  description = "List of email addresses to receive alert notifications"
  type        = list(string)
  default     = []
}

variable "error_threshold" {
  description = "Error rate threshold (errors per second) that triggers an alert"
  type        = number
  default     = 5
}

variable "alert_documentation_content" {
  description = "Custom documentation content for uptime check failure alerts"
  type        = string
  default     = "The FinOps Sentinel Cloud Run service uptime check has failed. This may indicate the service is down or unhealthy. Check the service status and logs for more details."
}

variable "smtp_host" {
  description = "SMTP server host for sending emails (optional)"
  type        = string
  default     = null
}

variable "smtp_port" {
  description = "SMTP server port (optional)"
  type        = number
  default     = null
}

variable "smtp_starttls" {
  description = "Enable STARTTLS for SMTP connection"
  type        = string
  default     = "true"
}

variable "smtp_from_email" {
  description = "From email address for SMTP (optional)"
  type        = string
  default     = null
}

variable "smtp_user" {
  description = "SMTP username for authentication (optional)"
  type        = string
  default     = null
}

variable "smtp_password" {
  description = "SMTP password for authentication (optional, stored in Secret Manager)"
  type        = string
  sensitive   = true
  default     = null
}
