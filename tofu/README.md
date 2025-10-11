# GCP FinOps Sentinel - Terraform/OpenTofu Module

This directory contains production-ready Terraform/OpenTofu Infrastructure-as-Code for deploying GCP FinOps Sentinel as a Cloud Run service with complete observability and security features.

## Overview

The `tofu/` directory provides a complete, battle-tested deployment configuration for GCP FinOps Sentinel that:

- **Deploys to Cloud Run Gen 2**: Serverless, auto-scaling deployment
- **Integrates with Budget Alerts**: Eventarc triggers from Pub/Sub budget topics
- **Manages IAM Automatically**: Creates service accounts with least-privilege permissions
- **Stores Configuration Securely**: Rules and secrets in Secret Manager
- **Enables Observability**: Optional action event publishing and monitoring
- **Supports Email Notifications**: SMTP integration for budget alerts

## Directory Structure

```
tofu/
├── README.md                        # This file
├── main.tf                          # Root module - invokes finops-sentinel module
├── variables.tf                     # Root-level variables with example values
└── finops-sentinel/                 # Reusable module for FinOps Sentinel
    ├── README.md                    # Comprehensive module documentation
    ├── main.tf                      # Cloud Run service and Eventarc trigger
    ├── variables.tf                 # Module input variables
    ├── datasources.tf               # Data sources (project metadata)
    ├── iam.tf                       # Service accounts and IAM bindings
    ├── pubsub.tf                    # Action event topic (optional)
    ├── rules.tf                     # Secret Manager secrets
    ├── monitoring.tf                # Uptime checks and alert policies
    └── outputs.tf                   # Module outputs
```

## Quick Start

### Prerequisites

1. **GCP Organization Access**: Organization-level IAM permissions for policy enforcement
2. **Container Image**: Build and push the FinOps Sentinel container to Artifact Registry
3. **Budget Alert Topic**: Existing [Pub/Sub topic receiving budget alerts](https://cloud.google.com/billing/docs/how-to/budgets-programmatic-notifications)
4. **Terraform/OpenTofu**: Version 1.0+ installed

### Step 1: Build and Push Container Image

```bash
# Build the container image
docker build -t us-docker.pkg.dev/YOUR-PROJECT/YOUR-REPO/gcp-finops-sentinel:latest .

# Push to Artifact Registry
docker push us-docker.pkg.dev/YOUR-PROJECT/YOUR-REPO/gcp-finops-sentinel:latest
```

### Step 2: Configure Variables

Copy the example configuration and customize:

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values
```

The [terraform.tfvars.example](terraform.tfvars.example) file provides comprehensive examples for:
- Production deployment with monitoring and email alerts
- Development deployment with dry-run mode
- Multi-region deployment with AWS SES
- Complete deployment checklist
- Security best practices

**Minimum required variables:**

```hcl
organization_id           = "123456789012"
project_id                = "my-finops-project"
terraform_service_account = "terraform@my-project.iam.gserviceaccount.com"
container_image           = "us-docker.pkg.dev/my-project/my-repo/gcp-finops-sentinel:v1.0.0"
budget_alert_topic_id     = "projects/my-project/topics/budget-alerts"
budget_alert_email        = "finops-alerts@example.com"
```

See [terraform.tfvars.example](terraform.tfvars.example) for all configuration options and examples.

### Step 3: Customize Rules Configuration (Optional)

Edit `variables.tf` to customize the `finops_rules_config` variable with your budget enforcement rules. See the [Rules Configuration](#rules-configuration) section below for examples.

### Step 4: Deploy

```bash
# Initialize Terraform/OpenTofu
tofu init

# Plan the deployment
tofu plan

# Apply the configuration
tofu apply
```

### Step 5: Verify Deployment

```bash
# Check Cloud Run service status
gcloud run services describe gcp-finops-sentinel \
  --region=us-central1 \
  --project=my-finops-project

# View logs
gcloud logging read "resource.type=cloud_run_revision AND \
  resource.labels.service_name=gcp-finops-sentinel" \
  --limit 50 \
  --project=my-finops-project
```

### Step 6: Test with Sample Budget Alerts

Use the provided testing scripts to send sample budget alerts:

```bash
# Test with a sample budget alert using the Python script
cd ..  # Navigate to repository root
python scripts/publish-budget-alert-event.py \
  --project-id=my-finops-project \
  --topic-id=budget-alerts \
  --cost-amount=850 \
  --budget-amount=1000 \
  --threshold-percent=85

# Or use gcloud directly
gcloud pubsub topics publish budget-alerts \
  --message='{"costAmount":850,"budgetAmount":1000,"costIntervalStart":"2025-01-01T00:00:00Z"}' \
  --attribute=billingAccountId=012345-ABCDEF-123456

# View action events (if enabled)
python scripts/consume-policy-action-events.py \
  --project-id=my-finops-project \
  --subscription-id=action-events-sub
```

**Available Testing Scripts:**
- `scripts/publish-budget-alert-event.py` - Publish test budget alerts to Pub/Sub
- `scripts/consume-policy-action-events.py` - Subscribe to and view action events
- `scripts/test-email-templates.py` - Test email templates with MailHog (local only)
- `scripts/debug-project-discovery.py` - Debug label-based project discovery

See [../scripts/](../scripts/) for more details on each script.

## Rules Configuration

The `finops_rules_config` variable defines when and what actions to take based on budget thresholds. Rules are stored securely in Secret Manager and automatically reloaded when updated.

### Example Rules

```hcl
variable "finops_rules_config" {
  type    = string
  default = jsonencode({
    rules = [
      # Rule 1: Warning threshold at 80%
      {
        name        = "warning_threshold"
        description = "Restrict expensive services at 80% budget"
        conditions = {
          threshold_percent = {
            operator = ">="
            value    = 80
          }
        }
        actions = [
          {
            type            = "log_only"
            target_projects = ["dev-project-1"]
            message         = "WARNING: Budget threshold reached at 80%"
          },
          {
            type            = "restrict_services"
            target_projects = ["dev-project-1"]
            services        = ["compute.googleapis.com", "run.googleapis.com"]
          }
        ]
      },
      # Rule 2: Critical threshold at 100%
      {
        name        = "critical_threshold"
        description = "Restrict all non-essential services at 100% budget"
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
            services = [
              "compute.googleapis.com",
              "run.googleapis.com",
              "cloudfunctions.googleapis.com",
              "container.googleapis.com"
            ]
          },
          {
            type         = "send_mail"
            to_emails    = ["finops-team@example.com"]
            template     = "budget_alert"
            custom_message = "CRITICAL: Budget exceeded. Services restricted."
          }
        ]
      },
      # Rule 3: Folder-based targeting
      {
        name        = "folder_targeting"
        description = "Apply policy to all projects in a folder"
        conditions = {
          threshold_percent = {
            operator = ">="
            value    = 90
          }
        }
        actions = [
          {
            target_folders = ["123456789012"]  # Folder ID
            type           = "restrict_services"
            services       = ["compute.googleapis.com"]
          }
        ]
      },
      # Rule 4: Label-based targeting
      {
        name        = "label_based_targeting"
        description = "Target projects by labels"
        conditions = {
          threshold_percent = {
            operator = ">="
            value    = 85
          }
        }
        actions = [
          {
            type = "restrict_services"
            target_labels = {
              environment = "dev"
              cost-center = "engineering"
            }
            services = ["run.googleapis.com", "cloudfunctions.googleapis.com"]
          }
        ]
      }
    ]
  })
}
```

### Rule Syntax

- **conditions**: Define when the rule triggers
  - `threshold_percent`: Budget threshold percentage with operator (`>=`, `>`, `==`, `<`, `<=`)
  - `billing_account_filter`: Optional billing account ID filter
  - `budget_id_filter`: Optional budget UUID filter

- **actions**: List of actions to execute
  - `type`: Action type (`restrict_services`, `apply_constraint`, `log_only`, `send_mail`)
  - **Targeting**: Choose one of:
    - `target_projects`: List of project IDs
    - `target_folders`: List of folder IDs
    - `target_labels`: Map of label key-value pairs for dynamic discovery
    - `target_organization`: Boolean to target entire organization

See the main repository [CLAUDE.md](../CLAUDE.md) for complete rule syntax and examples.

### Filtering Uptime Check Requests

When monitoring is enabled, the module creates uptime checks that send test budget alerts every 15 minutes to verify the service is healthy. To prevent these health checks from triggering enforcement rules, use `budget_id_filter` and `billing_account_filter`:

```hcl
# Rule to catch and log uptime check requests without taking action
{
  name        = "uptime_check_health_monitor"
  description = "Log uptime check health requests without taking action"
  conditions = {
    threshold_percent       = {"operator" = ">=", "value" = 0}
    budget_id_filter        = "uptime-check-budget-id"
    billing_account_filter  = "uptime-check-billing-account"
  }
  actions = [
    {
      type    = "log_only"
      message = "Health check received from monitoring uptime check - no action taken"
    }
  ]
}
```

**How it works:**
1. Uptime check sends budget alert with specific `budgetId` and `billingAccountId` (see [monitoring.tf](finops-sentinel/monitoring.tf))
2. This rule matches only uptime check requests using the filter conditions
3. `log_only` action logs the health check without triggering policies
4. Other rules ignore uptime checks because they don't match the filter criteria
5. Real budget alerts (with different IDs) bypass this rule and trigger enforcement

**Important:** Place this rule **first** in your rules list to ensure uptime checks are caught before other rules evaluate. Rules are evaluated in order, and the first matching rule determines the action.

## Module Architecture

```
┌─────────────────┐
│  Budget Alert   │
│   (Pub/Sub)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Eventarc      │
│    Trigger      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│   Cloud Run     │─────►│ Secret Manager   │
│ FinOps Sentinel │      │  (Rules Config)  │
└────────┬────────┘      └──────────────────┘
         │
         ├──────► Apply Organization Policies
         │
         ├──────► Restrict Services
         │
         ├──────► Send Email Notifications (optional)
         │
         └──────► Publish Action Events (optional)
                  │
                  ▼
         ┌─────────────────┐
         │   Pub/Sub       │
         │ Action Events   │
         └─────────────────┘
```

## Module Features

### 1. **Cloud Run Deployment**
- Serverless, auto-scaling execution
- Configurable CPU, memory, timeout
- Min/max instance scaling
- Custom labels and environment variables

### 2. **IAM Security**
- **FinOps Sentinel Service Account**:
  - `roles/orgpolicy.policyAdmin` (Organization level) - Apply organization policies
  - `roles/resourcemanager.organizationViewer` (Organization level) - View organization structure
  - `roles/resourcemanager.folderViewer` (Organization level) - View folder hierarchy for folder targeting
  - `roles/browser` (Organization level) - List projects for label-based discovery
  - `roles/serviceusage.serviceUsageAdmin` (per-project) - Enable/disable services
  - `roles/compute.instanceAdmin.v1` (per-project) - Manage compute resources (if needed)
  - `roles/secretmanager.secretAccessor` (Secret Manager secrets) - Read rules and SMTP credentials
  - `roles/pubsub.publisher` (Action events topic, if enabled) - Publish action events

- **Eventarc Trigger Service Account**:
  - `roles/run.invoker` (Cloud Run service) - Invoke the FinOps Sentinel service
  - `roles/eventarc.eventReceiver` (Eventarc) - Receive events from Eventarc
  - `roles/pubsub.subscriber` (Budget alert topic) - Subscribe to budget alerts

### 3. **Secret Manager Integration**
- Rules configuration stored securely
- SMTP password encryption (if provided)
- Automatic secret version management
- Mounted as volume in Cloud Run

### 4. **Observability**
- **Action Event Publishing**: Optional Pub/Sub topic for all policy actions
- **Cloud Run Logging**: Structured logs in Cloud Logging
- **Uptime Checks**: Monitor service health every 15 minutes
- **Alert Policies**: Email notifications for failures and errors
- **Dry-Run Mode**: Test rules without applying policies

### 5. **Monitoring & Alerting**
When `enable_monitoring = true`, the module creates:
- **Uptime Check**: Monitors `/health` endpoint
- **Alert Policy (Uptime Failure)**: Triggers when health check fails
- **Alert Policy (Service Errors)**: Triggers when 5xx error rate exceeds threshold
- **Email Notifications**: Sends alerts to configured addresses

## Variables Reference

See [variables.tf](variables.tf) for all available variables. Key variables:

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `organization_id` | GCP Organization ID | Yes | `123456789012` |
| `project_id` | Project ID for deployment | Yes | - |
| `terraform_service_account` | Terraform service account email | Yes | - |
| `container_image` | Container image URL in Artifact Registry | Yes | - |
| `budget_alert_topic_id` | Full Pub/Sub topic ID for budget alerts | Yes | - |
| `budget_alert_email` | Email for budget alerts and monitoring | Yes | - |
| `default_region` | Deployment region | No | `us-central1` |
| `finops_enable_action_events` | Enable action event publishing | No | `true` |
| `finops_dry_run` | Enable dry-run mode | No | `true` |
| `finops_rules_config` | JSON rules configuration | No | See examples |
| `smtp_host` | SMTP server hostname | No | `""` |
| `smtp_port` | SMTP port | No | `587` |
| `smtp_starttls` | Enable STARTTLS | No | `"true"` |
| `smtp_from_email` | From email address | No | `""` |
| `smtp_user` | SMTP username | No | `""` |
| `smtp_password` | SMTP password (sensitive) | No | `""` |

## Outputs

The module provides the following outputs:

- `service_name`: Cloud Run service name
- `service_url`: Cloud Run service URL
- `service_account_email`: FinOps Sentinel service account email
- `action_event_topic_id`: Pub/Sub topic ID for action events (if enabled)
- `rules_secret_id`: Secret Manager secret ID for rules
- `uptime_check_id`: Uptime check ID (if monitoring enabled)
- `alert_policy_uptime_id`: Uptime failure alert policy ID (if monitoring enabled)

See [finops-sentinel/outputs.tf](finops-sentinel/outputs.tf) for complete list.

## Updating Rules

To update rules after deployment:

1. Edit the `finops_rules_config` variable in `variables.tf` or `terraform.tfvars`
2. Run `tofu apply`
3. The module will create a new secret version
4. Cloud Run will automatically reload the configuration

```bash
# Example: Update rules and apply
tofu apply -var='finops_rules_config={"rules":[...]}'
```

## Dry-Run Mode

Test your rules without applying policies by setting `finops_dry_run = true`:

```hcl
variable "finops_dry_run" {
  default = true  # Enable dry-run mode
}
```

In dry-run mode:
- All rule evaluations are logged
- Policy actions are logged but NOT executed
- Action events are still published (if enabled)
- Perfect for testing rules before production deployment

## Email Notifications

Configure SMTP to enable email notifications via `send_mail` actions:

```hcl
# Gmail Example
smtp_host       = "smtp.gmail.com"
smtp_port       = 587
smtp_starttls   = "true"
smtp_from_email = "finops-alerts@example.com"
smtp_user       = "your-email@gmail.com"
smtp_password   = "app-password"  # Use App Passwords for Gmail

# AWS SES Example
smtp_host       = "email-smtp.us-east-1.amazonaws.com"
smtp_port       = 587
smtp_starttls   = "true"
smtp_from_email = "no-reply@example.com"
smtp_user       = "AKIAIOSFODNN7EXAMPLE"
smtp_password   = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
```

Then use `send_mail` actions in your rules:

```json
{
  "type": "send_mail",
  "to_emails": ["team@example.com"],
  "template": "budget_alert",
  "custom_message": "Budget exceeded. Review spending."
}
```

## Security Considerations

- **Least-Privilege IAM**: Service accounts have only required permissions
- **Secret Manager**: Sensitive data encrypted at rest
- **Private Cloud Run**: Service only accessible via Eventarc
- **Terraform State**: Store state in encrypted GCS bucket with versioning
- **SMTP Password**: Mark as sensitive, consider using env vars or Secret Manager

## Troubleshooting

### Cloud Run Service Not Starting

```bash
# Check Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision" --limit 50

# Describe the service
gcloud run services describe gcp-finops-sentinel --region=us-central1
```

### Eventarc Trigger Not Firing

```bash
# Check trigger status
gcloud eventarc triggers describe gcp-finops-sentinel-trigger --location=us-central1

# Verify trigger service account has pubsub.subscriber role
gcloud projects get-iam-policy PROJECT_ID --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:finops-sentinel-trigger@*"
```

### Rules Not Loading

```bash
# Check Secret Manager secret
gcloud secrets versions access latest --secret=gcp-finops-sentinel-rules

# Verify service account has secretmanager.secretAccessor role
gcloud secrets get-iam-policy gcp-finops-sentinel-rules
```

### Policies Not Applying

1. **Check Dry-Run Mode**: Ensure `finops_dry_run = false`
2. **Verify IAM Permissions**: Service account needs `roles/orgpolicy.policyAdmin`
3. **Review Logs**: Check Cloud Run logs for error messages
4. **Test Rule Conditions**: Verify threshold conditions match budget alert data

## License

Apache License 2.0 - See [LICENSE](../LICENSE) file for details.

## Support

For issues, questions, or contributions:
- Review the main [README.md](../README.md) and [CLAUDE.md](../CLAUDE.md)
- Check existing GitHub issues
- Open a new issue with detailed description and logs
