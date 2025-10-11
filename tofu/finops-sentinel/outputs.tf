output "service_name" {
  description = "Name of the Cloud Run service"
  value       = google_cloud_run_v2_service.finops_sentinel.name
}

output "service_id" {
  description = "Full ID of the Cloud Run service"
  value       = google_cloud_run_v2_service.finops_sentinel.id
}

output "service_url" {
  description = "URL of the Cloud Run service"
  value       = google_cloud_run_v2_service.finops_sentinel.uri
}

output "service_account_email" {
  description = "Email of the service account used by the Cloud Run service"
  value       = google_service_account.finops_sentinel.email
}

output "eventarc_trigger_name" {
  description = "Name of the Eventarc trigger"
  value       = google_eventarc_trigger.budget_alert_trigger.name
}

output "eventarc_trigger_id" {
  description = "Full ID of the Eventarc trigger"
  value       = google_eventarc_trigger.budget_alert_trigger.id
}

output "rules_secret_id" {
  description = "Secret Manager secret ID for rules configuration"
  value       = google_secret_manager_secret.rules_config.secret_id
}

output "rules_secret_version" {
  description = "Latest version of the rules configuration secret"
  value       = google_secret_manager_secret_version.rules_config_version.name
}

output "action_event_topic_id" {
  description = "Pub/Sub topic ID for policy action events (if enabled)"
  value       = var.enable_action_events ? google_pubsub_topic.action_events[0].id : ""
}

output "action_event_topic_name" {
  description = "Pub/Sub topic name for policy action events (if enabled)"
  value       = var.enable_action_events ? google_pubsub_topic.action_events[0].name : ""
}

# Monitoring outputs
output "uptime_check_id" {
  description = "ID of the uptime check (if monitoring is enabled)"
  value       = var.enable_monitoring ? google_monitoring_uptime_check_config.finops_sentinel[0].uptime_check_id : ""
}

output "uptime_check_name" {
  description = "Name of the uptime check (if monitoring is enabled)"
  value       = var.enable_monitoring ? google_monitoring_uptime_check_config.finops_sentinel[0].name : ""
}

output "notification_channel_ids" {
  description = "IDs of the notification channels (if monitoring is enabled)"
  value       = var.enable_monitoring && length(var.alert_email_addresses) > 0 ? [for channel in google_monitoring_notification_channel.email : channel.id] : []
}

output "alert_policy_uptime_id" {
  description = "ID of the uptime check failure alert policy (if monitoring is enabled)"
  value       = var.enable_monitoring && length(var.alert_email_addresses) > 0 ? google_monitoring_alert_policy.uptime_check_failure[0].id : ""
}

output "alert_policy_errors_id" {
  description = "ID of the service errors alert policy (if monitoring is enabled)"
  value       = var.enable_monitoring && length(var.alert_email_addresses) > 0 ? google_monitoring_alert_policy.service_errors[0].id : ""
}
