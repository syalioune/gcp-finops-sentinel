# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/pubsub_topic
# Optional Pub/Sub topic for policy action events (observability and auditing)
resource "google_pubsub_topic" "action_events" {
  count   = var.enable_action_events ? 1 : 0
  project = var.project_id
  name    = "${var.service_name}-action-events"

  message_retention_duration = "86400s" # 1 day

  labels = merge(
    {
      purpose    = "finops-action-events"
      managed_by = "terraform"
    },
    var.labels
  )

  depends_on = [
    google_project_service.required_apis
  ]
}

# Local value to get the topic ID (either created or empty)
locals {
  action_event_topic_id = var.enable_action_events ? google_pubsub_topic.action_events[0].id : ""
}
