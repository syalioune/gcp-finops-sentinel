# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/monitoring_uptime_check_config
# Uptime check for Cloud Run service health monitoring
resource "google_monitoring_uptime_check_config" "finops_sentinel" {
  count = var.enable_monitoring ? 1 : 0

  project            = var.project_id
  display_name       = "${var.service_name}-uptime-check"
  timeout            = "10s"
  period             = "900s"
  log_check_failures = true

  http_check {
    path                = "/"
    port                = 443
    use_ssl             = true
    validate_ssl        = false
    request_method      = "POST"
    content_type        = "USER_PROVIDED"
    custom_content_type = "application/json"

    # CloudEvent headers required by Pub/Sub push subscriptions
    headers = {
      "ce-id"          = "uptime-check-health-${timestamp()}"
      "ce-specversion" = "1.0"
      "ce-time"        = timestamp()
      "ce-type"        = "google.cloud.pubsub.topic.v1.messagePublished"
      "ce-source"      = "//pubsub.googleapis.com/projects/${var.project_id}/topics/budget-alerts"
    }

    # CloudEvent format matching Pub/Sub push subscription with budget alert data
    # Using low threshold (25%) so health checks don't trigger critical rules
    body = base64encode(jsonencode({
      message = {
        # Budget alert notification data (base64-encoded JSON)
        data = base64encode(jsonencode({
          budgetDisplayName      = "uptime-check-test-budget"
          alertThresholdExceeded = 0.25
          costAmount             = 250.00
          costIntervalStart      = "2019-01-01T00:00:00Z"
          budgetAmount           = 1000.00
          budgetAmountType       = "SPECIFIED_AMOUNT"
          currencyCode           = "USD"
        }))
        attributes = {
          budgetId         = "uptime-check-budget-id"
          billingAccountId = "uptime-check-billing-account"
        }
      }
      subscription = "projects/${var.project_id}/subscriptions/finops-sentinel-health-check"
    }))
    accepted_response_status_codes {
      status_class = "STATUS_CLASS_2XX"
    }
    service_agent_authentication {
      type = "OIDC_TOKEN"
    }
  }

  monitored_resource {
    type = "cloud_run_revision"
    labels = {
      project_id   = var.project_id
      service_name = google_cloud_run_v2_service.finops_sentinel.name
      location     = var.region
    }
  }

  checker_type = "STATIC_IP_CHECKERS"

  depends_on = [
    google_cloud_run_v2_service.finops_sentinel,
    google_project_service.monitoring_api
  ]

  lifecycle {
    ignore_changes = [ monitored_resource[0].labels ]
  }
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/monitoring_notification_channel
# Email notification channel for alerts
resource "google_monitoring_notification_channel" "email" {
  count = var.enable_monitoring && length(var.alert_email_addresses) > 0 ? length(var.alert_email_addresses) : 0

  project      = var.project_id
  display_name = "FinOps Sentinel Alert - ${var.alert_email_addresses[count.index]}"
  type         = "email"

  labels = {
    email_address = var.alert_email_addresses[count.index]
  }

  enabled = true

  depends_on = [google_project_service.monitoring_api]
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/monitoring_alert_policy
# Alert policy for uptime check failures
resource "google_monitoring_alert_policy" "uptime_check_failure" {
  count = var.enable_monitoring && length(var.alert_email_addresses) > 0 ? 1 : 0

  project      = var.project_id
  display_name = "${var.service_name} - Uptime Check Failure"
  combiner     = "OR"

  conditions {
    display_name = "Uptime check failure"

    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND metric.type = \"monitoring.googleapis.com/uptime_check/check_passed\" AND metric.label.check_id = \"${google_monitoring_uptime_check_config.finops_sentinel[0].uptime_check_id}\""
      duration        = "60s"
      comparison      = "COMPARISON_GT"
      threshold_value = 1.0

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_NEXT_OLDER"
        cross_series_reducer = "REDUCE_COUNT_FALSE"
        group_by_fields = [
          "resource.label.project_id",
          "resource.label.service_name",
          "resource.label.revision_name",
          "resource.label.location",
          "resource.label.configuration_name"
        ]
      }

      trigger {
        count = 1
      }
    }
  }

  notification_channels = [for channel in google_monitoring_notification_channel.email : channel.id]

  alert_strategy {
    auto_close = "1800s"
  }

  documentation {
    content   = var.alert_documentation_content
    mime_type = "text/markdown"
  }

  enabled = true

  depends_on = [
    google_monitoring_uptime_check_config.finops_sentinel,
    google_monitoring_notification_channel.email
  ]
}

# https://registry.terraform.io/providers/hashicorp/google/latest/docs/resources/monitoring_alert_policy
# Alert policy for Cloud Run service errors
resource "google_monitoring_alert_policy" "service_errors" {
  count = var.enable_monitoring && length(var.alert_email_addresses) > 0 ? 1 : 0

  project      = var.project_id
  display_name = "${var.service_name} - Service Errors"
  combiner     = "OR"

  conditions {
    display_name = "High error rate"

    condition_threshold {
      filter          = "resource.type = \"cloud_run_revision\" AND resource.labels.service_name = \"${google_cloud_run_v2_service.finops_sentinel.name}\" AND metric.type = \"run.googleapis.com/request_count\" AND metric.labels.response_code_class = \"5xx\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = var.error_threshold

      aggregations {
        alignment_period     = "60s"
        per_series_aligner   = "ALIGN_RATE"
        cross_series_reducer = "REDUCE_SUM"
        group_by_fields = [
          "resource.label.service_name"
        ]
      }

      trigger {
        count = 1
      }
    }
  }

  notification_channels = [for channel in google_monitoring_notification_channel.email : channel.id]

  alert_strategy {
    auto_close = "1800s"
  }

  documentation {
    content   = "The FinOps Sentinel Cloud Run service is experiencing elevated error rates. Check logs for details and verify the service configuration."
    mime_type = "text/markdown"
  }

  enabled = true

  depends_on = [
    google_cloud_run_v2_service.finops_sentinel,
    google_monitoring_notification_channel.email
  ]
}

# Enable Monitoring API
resource "google_project_service" "monitoring_api" {
  count = var.enable_monitoring ? 1 : 0

  project = var.project_id
  service = "monitoring.googleapis.com"

  disable_on_destroy = false
}
