# Terraform/OpenTofu Deployment Guide

This guide shows how to deploy GCP FinOps Sentinel using Terraform or OpenTofu.

## Overview

GCP FinOps Sentinel can be deployed using infrastructure-as-code with either:
- **Terraform** (HashiCorp)
- **OpenTofu** (Open-source fork)

Both tools use the same HCL configuration files.

## Prerequisites

### Required Tools

- Terraform ≥ 1.0 or OpenTofu ≥ 1.6
- gcloud CLI (authenticated)
- GCP Project with billing enabled

### Required GCP Permissions

Your deployment service account needs:
- `roles/cloudfunctions.admin` - To create Cloud Functions
- `roles/iam.serviceAccountAdmin` - To create service accounts
- `roles/pubsub.admin` - To create Pub/Sub topics
- `roles/storage.admin` - To create Cloud Storage buckets
- `roles/resourcemanager.organizationAdmin` - To grant org-level permissions

### Required GCP APIs

Enable these APIs in your project:

```bash
gcloud services enable cloudfunctions.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  pubsub.googleapis.com \
  cloudresourcemanager.googleapis.com \
  orgpolicy.googleapis.com \
  --project=YOUR_PROJECT_ID
```

## Quick Start

### 1. Use the Production-Ready Module

We provide a complete, production-ready OpenTofu/Terraform module in the `tofu/` directory:

- **[tofu/](../tofu/)** - Complete Cloud Run deployment with monitoring, secrets, and IAM (recommended)

### 2. Copy the Module

```bash
# Copy the production module
cp -r tofu/ my-deployment/
cd my-deployment/
```

### 3. Configure Variables

Edit `terraform.tfvars`:

```hcl
project_id      = "your-gcp-project"
region          = "us-central1"
organization_id = "123456789012"

# Optional: Enable features
enable_action_events = true
enable_email_notifications = false
```

### 4. Initialize and Deploy

```bash
# Initialize Terraform/OpenTofu
terraform init  # or: tofu init

# Review planned changes
terraform plan  # or: tofu plan

# Deploy infrastructure
terraform apply  # or: tofu apply
```

## Deployment Features

### Production-Ready Cloud Run Deployment

The `tofu/` module provides a complete production deployment with:

**Core Features:**
- **Cloud Run Gen 2**: Serverless, auto-scaling deployment
- **Eventarc Integration**: Automatic triggering from Pub/Sub budget alerts
- **Secret Manager**: Secure storage for rules configuration and SMTP credentials
- **IAM Security**: Least-privilege service accounts with organization-level permissions

**Observability:**
- **Action Event Publishing**: Optional Pub/Sub topic for policy action auditing
- **Uptime Checks**: Monitor service health every 15 minutes
- **Alert Policies**: Email notifications for failures and errors
- **Cloud Logging**: Structured logs for debugging and monitoring

**Email Notifications:**
- **SMTP Integration**: Send HTML emails via configured SMTP server
- **Jinja2 Templates**: Customizable email templates
- **Dry-Run Mode**: Test rules without applying policies

**See**: [tofu/README.md](../tofu/README.md) for complete documentation and usage examples

## Configuration

### Environment Variables

The Cloud Function requires these environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `ORGANIZATION_ID` | GCP Organization ID | Yes |
| `RULES_CONFIG_PATH` | Path to rules file | Yes (default: `/workspace/rules.json`) |
| `ACTION_EVENT_TOPIC` | Pub/Sub topic for action events | No |
| `DRY_RUN` | Enable dry-run mode | No (default: `false`) |
| `LOG_LEVEL` | Logging level | No (default: `INFO`) |
| `SMTP_HOST` | SMTP server for emails | No |
| `SMTP_PORT` | SMTP port | No (default: `587` for TLS, `25` for non-TLS) |
| `SMTP_USE_TLS` | Enable STARTTLS for SMTP | No (default: `true`) |
| `SMTP_USER` | SMTP authentication username | No |
| `SMTP_PASSWORD` | SMTP authentication password | No |
| `SMTP_FROM_EMAIL` | From email address | No |
| `TEMPLATE_DIR` | Custom email template directory | No |

### Rules Configuration

Rules can be provided in two ways:

#### 1. Inline Configuration (Small Rulesets)

```hcl
locals {
  rules_config = {
    rules = [
      {
        name = "critical_budget_breach"
        description = "Restrict compute when budget exceeds 100%"
        conditions = {
          threshold_percent = {
            operator = ">="
            value    = 100
          }
        }
        actions = [
          {
            type = "restrict_services"
            target_projects = ["prod-project-1", "prod-project-2"]
            services = ["compute.googleapis.com"]
          }
        ]
      }
    ]
  }
}

resource "google_cloudfunctions2_function" "finops_sentinel" {
  # ...
  service_config {
    environment_variables = {
      RULES_CONFIG = jsonencode(local.rules_config)
    }
  }
}
```

#### 2. External File (Recommended)

```hcl
resource "google_storage_bucket_object" "rules_config" {
  name   = "rules.json"
  bucket = google_storage_bucket.function_source.name
  source = "${path.module}/rules.json"
}

# Function reads from RULES_CONFIG_PATH=/workspace/rules.json
```

## IAM Permissions

### Service Account Creation

Create a dedicated service account for the function:

```hcl
resource "google_service_account" "finops_sentinel" {
  account_id   = "finops-sentinel"
  display_name = "GCP FinOps Sentinel"
  description  = "Service account for budget enforcement"
}
```

### Required Roles

Grant these roles at organization level:

```hcl
# Browser role - for project discovery
resource "google_organization_iam_member" "browser" {
  org_id = var.organization_id
  role   = "roles/browser"
  member = "serviceAccount:${google_service_account.finops_sentinel.email}"
}

# Org Policy Admin - for policy enforcement
resource "google_organization_iam_member" "orgpolicy_admin" {
  org_id = var.organization_id
  role   = "roles/orgpolicy.policyAdmin"
  member = "serviceAccount:${google_service_account.finops_sentinel.email}"
}

# Pub/Sub Publisher - for action events (topic-level, least privilege)
resource "google_pubsub_topic_iam_member" "publisher" {
  count  = var.enable_action_events ? 1 : 0
  topic  = google_pubsub_topic.action_events[0].name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.finops_sentinel.email}"
}
```

**See**: [docs/IAM_PERMISSIONS.md](IAM_PERMISSIONS.md) for detailed permission requirements.

## Pub/Sub Topics

### Budget Alerts Topic

This topic receives budget alert notifications from GCP Budgets:

```hcl
resource "google_pubsub_topic" "budget_alerts" {
  name = "budget-alerts"
}
```

Configure your GCP Budgets to publish to this topic via the Cloud Console or API.

### Action Events Topic (Optional)

Publishes policy action events for observability:

```hcl
resource "google_pubsub_topic" "action_events" {
  count = var.enable_action_events ? 1 : 0
  name  = "finops-action-events"
}

resource "google_pubsub_subscription" "action_events_pull" {
  count = var.enable_action_events ? 1 : 0
  name  = "finops-action-events-sub"
  topic = google_pubsub_topic.action_events[0].name

  ack_deadline_seconds = 20
  message_retention_duration = "604800s"  # 7 days
}
```

## Email Notifications (Optional)

To enable email notifications:

```hcl
resource "google_cloudfunctions2_function" "finops_sentinel" {
  service_config {
    environment_variables = {
      SMTP_HOST       = "smtp.gmail.com"
      SMTP_PORT       = "587"
      SMTP_USE_TLS    = "true"
      SMTP_FROM_EMAIL = "finops-alerts@example.com"
      # Store SMTP credentials in Secret Manager (recommended)
    }

    secret_environment_variables {
      key        = "SMTP_PASSWORD"
      project_id = var.project_id
      secret     = google_secret_manager_secret.smtp_password.secret_id
      version    = "latest"
    }
  }
}

resource "google_secret_manager_secret" "smtp_password" {
  secret_id = "finops-smtp-password"

  replication {
    automatic = true
  }
}
```

## Monitoring and Alerts

### Cloud Function Metrics

Monitor function execution:

```hcl
resource "google_monitoring_alert_policy" "function_errors" {
  display_name = "FinOps Sentinel - High Error Rate"
  combiner     = "OR"

  conditions {
    display_name = "Error rate > 5%"

    condition_threshold {
      filter          = "resource.type=\"cloud_function\" AND resource.labels.function_name=\"gcp-finops-sentinel\" AND metric.type=\"cloudfunctions.googleapis.com/function/execution_count\" AND metric.labels.status!=\"ok\""
      duration        = "300s"
      comparison      = "COMPARISON_GT"
      threshold_value = 5

      aggregations {
        alignment_period   = "60s"
        per_series_aligner = "ALIGN_RATE"
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]
}
```

### Action Event Monitoring

Monitor policy enforcement actions:

```hcl
resource "google_monitoring_alert_policy" "failed_actions" {
  count        = var.enable_action_events ? 1 : 0
  display_name = "FinOps Sentinel - Failed Policy Actions"

  conditions {
    display_name = "Policy action failures detected"

    condition_matched_log {
      filter = <<-EOT
        resource.type="cloud_function"
        resource.labels.function_name="gcp-finops-sentinel"
        jsonPayload.success=false
      EOT
    }
  }
}
```

## Testing Deployment

### 1. Publish Test Budget Alert

```bash
# Set variables
PROJECT_ID="your-project"
TOPIC="budget-alerts"

# Publish test message
gcloud pubsub topics publish $TOPIC \
  --project=$PROJECT_ID \
  --message='{"costAmount":1200,"budgetAmount":1000}' \
  --attribute=billingAccountId=012345-ABCDEF-123456,budgetId=test-budget-123
```

### 2. Check Function Logs

```bash
gcloud functions logs read gcp-finops-sentinel \
  --project=$PROJECT_ID \
  --limit=50
```

### 3. Verify Action Events

```bash
# Pull action events
gcloud pubsub subscriptions pull finops-action-events-sub \
  --project=$PROJECT_ID \
  --auto-ack \
  --limit=10
```

## Troubleshooting

### Function Not Triggering

**Check:**
1. Budget alerts are publishing to correct topic
2. Function has Pub/Sub trigger configured
3. Service account has `pubsub.subscriber` on topic

```bash
# Verify function trigger
gcloud functions describe gcp-finops-sentinel \
  --project=$PROJECT_ID \
  --gen2 \
  --format="value(eventTrigger)"
```

### Permission Denied Errors

**Check IAM roles:**

```bash
# Verify organization-level permissions
gcloud organizations get-iam-policy $ORG_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:finops-sentinel@$PROJECT_ID.iam.gserviceaccount.com"
```

**See**: [docs/IAM_PERMISSIONS.md](IAM_PERMISSIONS.md#troubleshooting-permission-issues)

### Project Discovery Returns 0 Projects

**Debug with script:**

```bash
# Run from function environment
gcloud functions call gcp-finops-sentinel \
  --project=$PROJECT_ID \
  --data='{"test":"discovery"}'
```

**See**: [CLAUDE.md - Debug Project Discovery](../CLAUDE.md#debug-project-discovery-by-labels)

## State Management

### Local State (Development)

```hcl
# Default - state stored locally
terraform {
  # No backend configuration
}
```

### Remote State (Production)

#### Google Cloud Storage Backend

```hcl
terraform {
  backend "gcs" {
    bucket = "my-terraform-state"
    prefix = "finops-sentinel"
  }
}
```

#### Terraform Cloud Backend

```hcl
terraform {
  backend "remote" {
    organization = "my-org"
    workspaces {
      name = "finops-sentinel-prod"
    }
  }
}
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy FinOps Sentinel

on:
  push:
    branches: [main]
    paths:
      - 'terraform/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: hashicorp/setup-terraform@v3
        with:
          terraform_version: 1.6.0

      - name: Terraform Init
        run: terraform init
        working-directory: ./terraform

      - name: Terraform Plan
        run: terraform plan
        working-directory: ./terraform

      - name: Terraform Apply
        if: github.ref == 'refs/heads/main'
        run: terraform apply -auto-approve
        working-directory: ./terraform
```

## Cleanup

To destroy all resources:

```bash
# Review resources to be destroyed
terraform plan -destroy

# Destroy all resources
terraform destroy

# Or with auto-approve (be careful!)
terraform destroy -auto-approve
```

## Best Practices

1. **Use Remote State** - Store state in GCS or Terraform Cloud
2. **Separate Environments** - Use workspaces or separate state files for dev/staging/prod
3. **Version Lock** - Pin provider versions in `versions.tf`
4. **Module Versioning** - Use versioned modules for reusability
5. **Secret Management** - Never commit secrets, use Secret Manager
6. **Least Privilege** - Grant minimum required IAM permissions
7. **Enable Monitoring** - Set up alerts for function errors and failed actions
8. **Test in Dev First** - Always test rule changes in non-production first

## Module Documentation

- **[tofu/](../tofu/)** - Production-ready OpenTofu/Terraform module with complete documentation
- **[tofu/finops-sentinel/](../tofu/finops-sentinel/)** - Reusable module for Cloud Run deployment

## Additional Resources

- [IAM Permissions Guide](IAM_PERMISSIONS.md)
- [Local Development Guide](LOCAL_DEVELOPMENT.md)
- [Terraform Google Provider Docs](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [OpenTofu Documentation](https://opentofu.org/docs/)

## Support

For issues or questions:
- [GitHub Issues](https://github.com/syalioune/gcp-finops-sentinel/issues)
- [GitHub Discussions](https://github.com/syalioune/gcp-finops-sentinel/discussions)
