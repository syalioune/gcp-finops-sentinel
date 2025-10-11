# FinOps Sentinel Terraform Module

This module deploys the GCP FinOps Sentinel as a Cloud Run service triggered by Eventarc from Pub/Sub budget alert topics.

## Overview

The FinOps Sentinel automatically enforces policy actions in response to GCP budget alerts, helping control costs by:

- Restricting GCP service usage when budget thresholds are exceeded
- Applying organization policy constraints (e.g., disable external IPs, restrict machine types)
- Filtering by billing account ID and budget ID (UUID)
- Targeting multiple projects with configurable rules

## Architecture

```
Budget Alert → Pub/Sub Topic → Eventarc → Cloud Run (FinOps Sentinel) → Apply Policies
```

## Features

- **Cloud Run Gen 2**: Scalable, serverless deployment
- **Eventarc Integration**: Event-driven trigger from Pub/Sub budget alerts
- **Secret Manager**: Secure storage of rules configuration
- **IAM Management**: Automated service account and permissions setup
- **Multi-Project Support**: Apply policies across multiple target projects
- **Observability**: Optional action event publishing to Pub/Sub
- **Monitoring & Alerting**: Optional uptime checks, alert policies, and email notifications

## Usage

### Basic Example

```hcl
module "finops_sentinel" {
  source = "./modules/finops-sentinel"

  project_id         = "my-landing-zone-project"
  organization_id    = "123456789012"
  region            = "europe-west9"
  container_image   = "europe-west9-docker.pkg.dev/my-project/cloud-functions/gcp-finops-sentinel:latest"

  # From budgets module output
  budget_alert_topic_id = module.budgets.budget_pubsub_topic_id

  # Rules configuration
  rules_config = jsonencode({
    rules = [
      {
        name        = "critical_budget_breach"
        description = "Restrict compute when budget exceeds 100%"
        conditions = {
          threshold_percent = {
            operator = ">="
            value    = 100
          }
        }
        actions = [
          {
            type            = "restrict_services"
            target_projects = ["dev-project-1", "prod-project-1"]
            services        = ["compute.googleapis.com"]
          }
        ]
      }
    ]
  })
}
```

### Advanced Example with Action Events and Monitoring

```hcl
module "finops_sentinel" {
  source = "./modules/finops-sentinel"

  project_id         = "my-landing-zone-project"
  organization_id    = "123456789012"
  region            = "europe-west9"
  container_image   = "europe-west9-docker.pkg.dev/my-project/cloud-functions/gcp-finops-sentinel:v1.0.0"

  budget_alert_topic_id = module.budgets.budget_pubsub_topic_id

  # Enable action event publishing (creates Pub/Sub topic automatically)
  enable_action_events = true

  # Enable monitoring and alerting
  enable_monitoring = true
  alert_email_addresses = [
    "team-platform@example.com",
    "sre-oncall@example.com"
  ]
  health_check_path = "/health"
  error_threshold   = 5  # Alert if more than 5 errors/second

  # Performance tuning
  cpu_limit      = "2"
  memory_limit   = "1Gi"
  timeout_seconds = 300
  max_instances  = 10
  min_instances  = 1

  log_level = "INFO"

  labels = {
    environment = "production"
    team        = "platform"
  }

  rules_config = jsonencode({
    rules = [
      {
        name        = "critical_budget_breach"
        description = "Restrict compute at 100% threshold"
        conditions = {
          threshold_percent = {
            operator = ">="
            value    = 100
          }
        }
        actions = [
          {
            type            = "restrict_services"
            target_projects = ["dev-project-1", "prod-project-1"]
            services        = ["compute.googleapis.com", "container.googleapis.com"]
          }
        ]
      },
      {
        name        = "warning_threshold"
        description = "Disable external IPs at 80%"
        conditions = {
          threshold_percent = {
            operator = ">="
            value    = 80
          }
        }
        actions = [
          {
            type            = "apply_constraint"
            target_projects = ["dev-project-2"]
            constraint      = "constraints/compute.vmExternalIpAccess"
            enforce         = true
          }
        ]
      },
      {
        name        = "billing_account_filter"
        description = "Control specific billing account"
        conditions = {
          threshold_percent = {
            operator = ">="
            value    = 75
          }
          billing_account_filter = "012345-6789AB-CDEF01"
        }
        actions = [
          {
            type            = "restrict_services"
            target_projects = ["dev-project-1", "dev-project-2"]
            services        = ["compute.googleapis.com"]
          }
        ]
      }
    ]
  })
}
```

## Inputs

| Name | Description | Type | Default | Required |
|------|-------------|------|---------|:--------:|
| project_id | GCP project ID where Cloud Run will be deployed | `string` | n/a | yes |
| organization_id | GCP Organization ID for policy enforcement | `string` | n/a | yes |
| container_image | Container image URL in Artifact Registry | `string` | n/a | yes |
| budget_alert_topic_id | Pub/Sub topic ID for budget alerts | `string` | n/a | yes |
| rules_config | Rules configuration as JSON string | `string` | n/a | yes |
| region | GCP region for deployment | `string` | `"europe-west9"` | no |
| service_name | Cloud Run service name | `string` | `"gcp-finops-sentinel"` | no |
| enable_action_events | Enable creation of action events Pub/Sub topic | `bool` | `false` | no |
| cpu_limit | CPU limit | `string` | `"1"` | no |
| memory_limit | Memory limit | `string` | `"512Mi"` | no |
| timeout_seconds | Request timeout in seconds | `number` | `300` | no |
| max_instances | Maximum instances | `number` | `10` | no |
| min_instances | Minimum instances | `number` | `0` | no |
| log_level | Logging level (DEBUG/INFO/WARNING/ERROR) | `string` | `"INFO"` | no |
| dry_run | Enable dry-run mode to test without applying policies | `bool` | `false` | no |
| labels | Additional resource labels | `map(string)` | `{}` | no |
| enable_monitoring | Enable uptime checks and alert policies | `bool` | `false` | no |
| health_check_path | Path for uptime health check endpoint | `string` | `"/health"` | no |
| alert_email_addresses | List of email addresses for alert notifications | `list(string)` | `[]` | no |
| error_threshold | Error rate threshold (errors/sec) for alerts | `number` | `5` | no |
| alert_documentation_content | Custom documentation for uptime check failure alerts | `string` | `"The FinOps Sentinel Cloud Run service uptime check has failed..."` | no |

## Outputs

| Name | Description |
|------|-------------|
| service_name | Cloud Run service name |
| service_id | Cloud Run service full ID |
| service_url | Cloud Run service URL |
| service_account_email | Service account email |
| eventarc_trigger_name | Eventarc trigger name |
| eventarc_trigger_id | Eventarc trigger full ID |
| rules_secret_id | Secret Manager secret ID for rules |
| rules_secret_version | Latest rules secret version |
| action_event_topic_id | Pub/Sub topic ID for action events (if enabled) |
| action_event_topic_name | Pub/Sub topic name for action events (if enabled) |
| uptime_check_id | Uptime check ID (if monitoring is enabled) |
| uptime_check_name | Uptime check name (if monitoring is enabled) |
| notification_channel_ids | Notification channel IDs (if monitoring is enabled) |
| alert_policy_uptime_id | Uptime check failure alert policy ID (if monitoring is enabled) |
| alert_policy_errors_id | Service errors alert policy ID (if monitoring is enabled) |

## Updating Rules

To update rules after deployment:

```bash
# Update the rules_config variable in your Terraform configuration
# Then apply the changes
tofu apply
```

The module will automatically create a new secret version and Cloud Run will reload the configuration.

## Monitoring and Debugging

### Monitoring Features

When `enable_monitoring = true`, the module automatically creates:

1. **Uptime Check**: Monitors the Cloud Run service health endpoint every 60 seconds
2. **Alert Policies**:
   - **Uptime Check Failure**: Triggers when the health check fails
   - **Service Errors**: Triggers when 5xx error rate exceeds the configured threshold
3. **Email Notifications**: Sends alerts to configured email addresses

Alert policies include:
- Auto-close after 30 minutes of recovery
- Rate limiting (one notification per 5 minutes max)
- Custom documentation in alert messages

## Security Considerations

- Rules configuration is stored in Secret Manager with encryption at rest
- Service accounts follow least-privilege principle
- Cloud Run service is private (only invoked by Eventarc)
- All IAM bindings are explicitly managed by Terraform

## References

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Eventarc Documentation](https://cloud.google.com/eventarc/docs)
- [Organization Policy Constraints](https://cloud.google.com/resource-manager/docs/organization-policy/org-policy-constraints)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)

## License

Apache License 2.0
