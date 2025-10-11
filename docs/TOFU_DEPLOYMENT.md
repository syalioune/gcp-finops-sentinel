# Terraform/OpenTofu Deployment Guide

Deploy GCP FinOps Sentinel using infrastructure-as-code with Terraform or OpenTofu.

---

## Quick Reference

| Aspect | Details |
|--------|---------|
| **Deployment Time** | 5-10 minutes |
| **Tool Versions** | Terraform ≥ 1.0 or OpenTofu ≥ 1.6 |
| **Resources Created** | Cloud Run service, Secret Manager secrets, Pub/Sub topics (2), Eventarc trigger, IAM bindings, Uptime checks |
| **Estimated Cost** | ~$10-30/month (depends on invocations) |
| **Production Module** | ✅ Available at [tofu/](../tofu/) |

---

## Minimum Setup (5 Minutes)

Use the production-ready module for fastest deployment:

```bash
# 1. Copy module
cp -r tofu/ my-deployment/ && cd my-deployment/

# 2. Configure (edit terraform.tfvars)
cat > terraform.tfvars <<EOF
project_id      = "your-gcp-project"
region          = "us-central1"
organization_id = "123456789012"
EOF

# 3. Deploy
tofu init && tofu apply
```

**That's it!** The module handles all IAM, secrets, monitoring, and Cloud Run configuration.

---

## Prerequisites

<details>
<summary><b>📋 Required Tools & Permissions</b> (click to expand)</summary>

### Tools Required

| Tool | Version | Purpose |
|------|---------|---------|
| **Terraform** or **OpenTofu** | ≥ 1.0 / ≥ 1.6 | Infrastructure provisioning |
| **gcloud CLI** | Latest | GCP authentication & API enablement |
| **GCP Project** | - | Must have billing enabled |

### GCP APIs to Enable

```bash
gcloud services enable \
  cloudfunctions.googleapis.com \
  cloudbuild.googleapis.com \
  cloudrun.googleapis.com \
  eventarc.googleapis.com \
  artifactregistry.googleapis.com \
  pubsub.googleapis.com \
  cloudresourcemanager.googleapis.com \
  orgpolicy.googleapis.com \
  secretmanager.googleapis.com \
  --project=YOUR_PROJECT_ID
```

### Deployment Service Account Permissions

Your deployment identity (user or service account) needs:

| Role | Purpose | Scope |
|------|---------|-------|
| `roles/run.admin` | Create Cloud Run services | Project |
| `roles/iam.serviceAccountAdmin` | Create service accounts | Project |
| `roles/pubsub.admin` | Create Pub/Sub topics | Project |
| `roles/secretmanager.admin` | Create Secret Manager secrets | Project |
| `roles/resourcemanager.organizationAdmin` | Grant org-level IAM to service account | Organization |
| `roles/eventarc.admin` | Create Eventarc triggers | Project |

</details>

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         GCP Organization                        │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │                    GCP Project (Deployment)                │ │
│  │                                                             │ │
│  │  ┌──────────────┐         ┌─────────────────────────────┐ │ │
│  │  │  GCP Budget  │─publish→│ Pub/Sub: budget-alerts      │ │ │
│  │  └──────────────┘         └────────┬────────────────────┘ │ │
│  │                                     │                       │ │
│  │                              Eventarc Trigger               │ │
│  │                                     ↓                       │ │
│  │  ┌───────────────────────────────────────────────────────┐ │ │
│  │  │         Cloud Run: gcp-finops-sentinel               │ │ │
│  │  │  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐ │ │ │
│  │  │  │ Rule Engine │→ │ Response     │→ │ Org Policy  │ │ │ │
│  │  │  │             │  │ Engine       │  │ API         │ │ │ │
│  │  │  └─────────────┘  └──────────────┘  └─────────────┘ │ │ │
│  │  │          ↓                  ↓                          │ │ │
│  │  │  ┌─────────────┐  ┌──────────────┐                   │ │ │
│  │  │  │ Secret Mgr  │  │ Pub/Sub:     │                   │ │ │
│  │  │  │ (rules.json)│  │ action-events│                   │ │ │
│  │  │  └─────────────┘  └──────────────┘                   │ │ │
│  │  └───────────────────────────────────────────────────────┘ │ │
│  │                                                             │ │
│  │  ┌───────────────────────────────────────────────────────┐ │ │
│  │  │ Service Account: finops-sentinel@...                  │ │ │
│  │  │ • roles/browser (org-level)                           │ │ │
│  │  │ • roles/orgpolicy.policyAdmin (org-level)             │ │ │
│  │  │ • roles/pubsub.publisher (topic-level)                │ │ │
│  │  └───────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Configuration

### Rules Configuration Options

<details>
<summary><b>Option 1: Secret Manager (Recommended for Production)</b></summary>

The production module uses Secret Manager for secure, updateable rules:

```hcl
# In tofu/ module - automatically configured
resource "google_secret_manager_secret" "rules_config" {
  secret_id = "finops-sentinel-rules"

  replication {
    automatic = true
  }
}

# Update rules without redeploying:
echo '{"rules":[...]}' | gcloud secrets versions add finops-sentinel-rules --data-file=-
```

**✅ Advantages:**
- Update rules without redeploying Cloud Run
- Automatic versioning and rollback
- Encrypted at rest
- Audit trail via Cloud Logging

</details>

<details>
<summary><b>Option 2: Environment Variable (Small Rulesets)</b></summary>

For simple deployments:

```hcl
resource "google_cloud_run_v2_service" "finops_sentinel" {
  template {
    containers {
      env {
        name  = "RULES_CONFIG"
        value = jsonencode({
          rules = [
            {
              name = "critical_budget_breach"
              conditions = {
                threshold_percent = { operator = ">=", value = 100 }
              }
              actions = [{
                type = "restrict_services"
                target_projects = ["prod-project-1"]
                services = ["compute.googleapis.com"]
              }]
            }
          ]
        })
      }
    }
  }
}
```

**❌ Limitations:**
- Environment variable size limit (32 KB)
- Requires redeployment to update rules
- Less secure (visible in console)

</details>

### Email Notifications Setup

<details>
<summary><b>SMTP Configuration (Optional)</b></summary>

Enable email notifications via environment variables and Secret Manager:

```hcl
resource "google_cloud_run_v2_service" "finops_sentinel" {
  template {
    containers {
      # Public SMTP settings
      env {
        name  = "SMTP_HOST"
        value = "smtp.gmail.com"
      }
      env {
        name  = "SMTP_PORT"
        value = "587"
      }
      env {
        name  = "SMTP_USE_TLS"
        value = "true"
      }
      env {
        name  = "SMTP_FROM_EMAIL"
        value = "finops-alerts@example.com"
      }

      # Sensitive credentials from Secret Manager
      env {
        name = "SMTP_USER"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.smtp_user.secret_id
            version = "latest"
          }
        }
      }
      env {
        name = "SMTP_PASSWORD"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.smtp_password.secret_id
            version = "latest"
          }
        }
      }
    }
  }
}
```

**Popular SMTP Providers:**
- **Gmail**: Use App Passwords (not regular password)
- **SendGrid**: Username=`apikey`, password=API key
- **AWS SES**: Get SMTP credentials from SES console
- **Mailgun**: SMTP credentials from Mailgun dashboard

**See:** `email-templates/README.md` for template customization

</details>

---

## Environment Variables Reference

<details>
<summary><b>📝 Complete Environment Variables List</b></summary>

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ORGANIZATION_ID` | GCP Organization ID | ✅ Yes | - |
| `RULES_CONFIG_PATH` | Path to rules file | ⚠️ If not using `RULES_CONFIG` | `/workspace/rules.json` |
| `RULES_CONFIG` | Rules as JSON/YAML string | ⚠️ If not using `RULES_CONFIG_PATH` | - |
| `ACTION_EVENT_TOPIC` | Pub/Sub topic for action auditing | ❌ No | - |
| `DRY_RUN` | Log actions without executing | ❌ No | `false` |
| `LOG_LEVEL` | Logging verbosity | ❌ No | `INFO` |
| `SMTP_HOST` | SMTP server hostname | ❌ No | - |
| `SMTP_PORT` | SMTP server port | ❌ No | `587` (TLS) |
| `SMTP_USE_TLS` | Enable STARTTLS | ❌ No | `true` |
| `SMTP_USER` | SMTP username | ❌ No | - |
| `SMTP_PASSWORD` | SMTP password | ❌ No | - |
| `SMTP_FROM_EMAIL` | Sender email address | ❌ No | `$SMTP_USER` |
| `TEMPLATE_DIR` | Custom email templates path | ❌ No | `/workspace/email-templates` |

</details>

---

## IAM Configuration

<details>
<summary><b>🔐 Service Account & IAM Roles</b></summary>

The production module automatically creates and configures the service account:

```hcl
# Service account creation
resource "google_service_account" "finops_sentinel" {
  account_id   = "finops-sentinel"
  display_name = "GCP FinOps Sentinel"
  description  = "Service account for budget enforcement"
}

# Organization-level permissions
resource "google_organization_iam_member" "browser" {
  org_id = var.organization_id
  role   = "roles/browser"
  member = "serviceAccount:${google_service_account.finops_sentinel.email}"
}

resource "google_organization_iam_member" "orgpolicy_admin" {
  org_id = var.organization_id
  role   = "roles/orgpolicy.policyAdmin"
  member = "serviceAccount:${google_service_account.finops_sentinel.email}"
}

# Topic-level permission (least privilege)
resource "google_pubsub_topic_iam_member" "publisher" {
  count  = var.enable_action_events ? 1 : 0
  topic  = google_pubsub_topic.action_events[0].name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.finops_sentinel.email}"
}
```

**See:** [IAM_PERMISSIONS.md](IAM_PERMISSIONS.md) for detailed permission requirements and troubleshooting

</details>

---

## Monitoring & Observability

<details>
<summary><b>📊 Built-in Monitoring Features</b></summary>

The production module includes comprehensive monitoring:

### Uptime Checks
- HTTP health checks every 15 minutes
- Validates Cloud Run service availability
- Alerts on consecutive failures

### Alert Policies
```hcl
# High error rate alert
resource "google_monitoring_alert_policy" "function_errors" {
  display_name = "FinOps Sentinel - High Error Rate"
  conditions {
    display_name = "Error rate > 5%"
    condition_threshold {
      filter     = "resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.labels.response_code_class=\"5xx\""
      comparison = "COMPARISON_GT"
      threshold_value = 5
      duration   = "300s"
    }
  }
  notification_channels = [var.alert_email]
}

# Failed policy actions
resource "google_monitoring_alert_policy" "failed_actions" {
  display_name = "FinOps Sentinel - Failed Policy Actions"
  conditions {
    display_name = "Policy enforcement failures"
    condition_matched_log {
      filter = <<-EOT
        resource.type="cloud_run_revision"
        resource.labels.service_name="gcp-finops-sentinel"
        jsonPayload.success=false
      EOT
    }
  }
}
```

### Action Event Publishing
Optional Pub/Sub topic for audit trail:
- Every policy action published as structured event
- Includes success/failure status, timestamps, details
- Subscribe for downstream integrations (SIEM, ticketing, analytics)

**See:** [CLAUDE.md - Policy Action Event Publishing](../CLAUDE.md#policy-action-event-publishing)

</details>

---

## Testing & Validation

<details>
<summary><b>✅ Post-Deployment Testing Steps</b></summary>

### 1. Verify Deployment

```bash
# Check Cloud Run service status
gcloud run services describe gcp-finops-sentinel \
  --project=$PROJECT_ID \
  --region=$REGION \
  --format="value(status.conditions)"

# Verify Eventarc trigger
gcloud eventarc triggers describe budget-alerts-trigger \
  --project=$PROJECT_ID \
  --location=$REGION
```

### 2. Publish Test Budget Alert

```bash
# Use the provided script
python scripts/publish-budget-alert-event.py \
  --project-id=$PROJECT_ID \
  --topic=budget-alerts \
  --cost=1200 \
  --budget=1000 \
  --threshold=120

# Or manually with gcloud
gcloud pubsub topics publish budget-alerts \
  --project=$PROJECT_ID \
  --message='{"costAmount":1200,"budgetAmount":1000}' \
  --attribute=billingAccountId=012345-ABCDEF-123456,budgetId=test-budget
```

### 3. Check Logs

```bash
# View Cloud Run logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=gcp-finops-sentinel" \
  --project=$PROJECT_ID \
  --limit=50 \
  --format=json

# View structured action events
gcloud pubsub subscriptions pull finops-action-events-sub \
  --project=$PROJECT_ID \
  --auto-ack \
  --limit=10
```

### 4. Verify Policy Applied (if not dry-run)

```bash
# Check organization policy on target project
gcloud org-policies describe gcp.restrictServiceUsage \
  --project=TARGET_PROJECT_ID \
  --effective
```

</details>

---

## Troubleshooting

<details>
<summary><b>🔧 Common Issues & Solutions</b></summary>

### ❌ Cloud Run Service Not Receiving Events

**Symptoms:** Budget alerts published but service never invoked

**Checklist:**
- [ ] Verify Eventarc trigger exists: `gcloud eventarc triggers list --location=$REGION`
- [ ] Check trigger's service account has `eventarc.eventReceiver` role
- [ ] Confirm budget alerts publishing to correct topic
- [ ] Review Eventarc audit logs for delivery failures

**Fix:**
```bash
# Grant required role
gcloud run services add-iam-policy-binding gcp-finops-sentinel \
  --region=$REGION \
  --member="serviceAccount:$EVENTARC_SA" \
  --role="roles/run.invoker"
```

---

### ❌ Permission Denied Errors

**Symptoms:** `403 Forbidden` or `PERMISSION_DENIED` in logs

**Checklist:**
- [ ] Service account has `roles/browser` at organization level
- [ ] Service account has `roles/orgpolicy.policyAdmin` at organization level
- [ ] IAM policy changes propagated (can take 80+ seconds)
- [ ] Organization ID is correct in environment variable

**Debug:**
```bash
# Verify organization IAM bindings
gcloud organizations get-iam-policy $ORG_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:finops-sentinel@$PROJECT_ID.iam.gserviceaccount.com"

# Should show roles/browser and roles/orgpolicy.policyAdmin
```

**See:** [IAM_PERMISSIONS.md - Troubleshooting](IAM_PERMISSIONS.md#troubleshooting-permission-issues)

---

### ❌ Project Discovery Returns 0 Projects

**Symptoms:** `target_labels` matching returns no projects despite labels existing

**Checklist:**
- [ ] Projects have correct labels: `gcloud projects list --filter='labels.env=prod'`
- [ ] Service account has `roles/browser` (required for project listing)
- [ ] Projects are ACTIVE (not pending deletion)
- [ ] Label syntax uses correct format: `{"env": "prod", "team": "backend"}`

**Debug:**
```bash
# Test label discovery with debug script
python scripts/debug-project-discovery.py \
  --labels env=prod team=backend \
  --org $ORG_ID \
  --compare-gcloud \
  --debug
```

**See:** [CLAUDE.md - Debug Project Discovery](../CLAUDE.md#debug-project-discovery-by-labels)

---

### ❌ Rules Not Updating After Secret Change

**Symptoms:** Updated rules in Secret Manager not reflected in enforcement

**Cause:** Cloud Run caches secret values until revision restart

**Fix:**
```bash
# Force new revision deployment (restarts all instances)
gcloud run services update gcp-finops-sentinel \
  --region=$REGION \
  --update-env-vars=FORCE_RESTART=$(date +%s)

# Or wait for next cold start (typically within 15 minutes)
```

---

### ❌ SMTP Email Sending Fails

**Symptoms:** `send_mail` actions fail with connection or authentication errors

**Checklist:**
- [ ] SMTP credentials stored in Secret Manager (not environment variables)
- [ ] Service account has `secretmanager.secretAccessor` role
- [ ] SMTP host/port/TLS settings correct for provider
- [ ] Network egress allowed from Cloud Run (not behind VPC restrictions)

**Gmail-specific:**
- [ ] Using App Password (not account password)
- [ ] 2FA enabled on Google account
- [ ] "Less secure apps" NOT required for App Passwords

**Test locally:**
```bash
# Set DRY_RUN=false to test actual SMTP connection
docker run -e SMTP_HOST=smtp.gmail.com \
  -e SMTP_USER=your-email@gmail.com \
  -e SMTP_PASSWORD=your-app-password \
  -e SMTP_PORT=587 \
  -e DRY_RUN=false \
  gcr.io/your-project/gcp-finops-sentinel:latest
```

</details>

---

## State Management

<details>
<summary><b>💾 State Backend Configuration</b></summary>

### Development (Local State)

```hcl
# No backend configuration - state stored locally
terraform {
  required_version = ">= 1.6"
}
```

**✅ Good for:** Local testing, experimentation
**❌ Avoid for:** Production, team collaboration

---

### Production (GCS Backend)

```hcl
terraform {
  backend "gcs" {
    bucket = "my-terraform-state"
    prefix = "finops-sentinel/prod"
  }
}
```

**Create backend bucket:**
```bash
gsutil mb -p $PROJECT_ID -l $REGION gs://my-terraform-state
gsutil versioning set on gs://my-terraform-state
```

**✅ Good for:** Production, team collaboration, disaster recovery

---

### Terraform Cloud Backend

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

**✅ Good for:** Managed state, built-in locking, remote runs, RBAC

</details>

---

## CI/CD Integration

<details>
<summary><b>🚀 GitHub Actions Example</b></summary>

```yaml
name: Deploy FinOps Sentinel

on:
  push:
    branches: [main]
    paths:
      - 'tofu/**'
      - '.github/workflows/deploy.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write  # For Workload Identity Federation

    steps:
      - uses: actions/checkout@v4

      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}

      - uses: opentofu/setup-opentofu@v1
        with:
          tofu_version: 1.6.0

      - name: Terraform Init
        run: tofu init
        working-directory: ./tofu

      - name: Terraform Plan
        run: tofu plan -out=tfplan
        working-directory: ./tofu

      - name: Terraform Apply
        if: github.ref == 'refs/heads/main'
        run: tofu apply tfplan
        working-directory: ./tofu
```

</details>

---

## Best Practices

<details>
<summary><b>⭐ Production Deployment Recommendations</b></summary>

### Security
- ✅ **Use Secret Manager** for rules and SMTP credentials
- ✅ **Grant least privilege** IAM roles (topic-level for Pub/Sub, not project-level)
- ✅ **Enable VPC Service Controls** for sensitive projects
- ✅ **Audit action events** via Pub/Sub subscription to SIEM
- ❌ **Never commit** secrets or `terraform.tfvars` with sensitive data

### Reliability
- ✅ **Use remote state** (GCS or Terraform Cloud)
- ✅ **Enable state locking** to prevent concurrent modifications
- ✅ **Version pin providers** in `versions.tf`
- ✅ **Set up monitoring alerts** for function errors and failed actions
- ✅ **Test in dev environment** before production

### Operations
- ✅ **Separate environments** using workspaces or separate state files
- ✅ **Document rule changes** in CHANGELOG.md
- ✅ **Use dry-run mode** to validate new rules: `DRY_RUN=true`
- ✅ **Subscribe to action events** for observability
- ✅ **Review logs regularly** for unexpected behavior

### Cost Optimization
- ✅ **Use Cloud Run** (pay-per-invocation, not always-on)
- ✅ **Set reasonable concurrency** (default: 80 concurrent requests)
- ✅ **Enable action events** only if needed for auditing
- ✅ **Use Pub/Sub retention** (7 days default) to control storage costs

</details>

---

## Additional Resources

| Resource | Link |
|----------|------|
| **Production Module** | [tofu/](../tofu/) - Complete deployment with monitoring |
| **IAM Permissions** | [IAM_PERMISSIONS.md](IAM_PERMISSIONS.md) - Detailed permission guide |
| **Local Development** | [LOCAL_DEVELOPMENT.md](LOCAL_DEVELOPMENT.md) - Docker Compose setup |
| **Email Templates** | [email-templates/README.md](../email-templates/README.md) - Template customization |
| **Project Documentation** | [CLAUDE.md](../CLAUDE.md) - Architecture & development guide |
| **Terraform Provider** | [Google Provider Docs](https://registry.terraform.io/providers/hashicorp/google/latest/docs) |
| **OpenTofu Docs** | [opentofu.org/docs](https://opentofu.org/docs/) |

---

## Cleanup

**⚠️ Warning:** This will destroy all deployed resources.

```bash
# Review resources to be destroyed
tofu plan -destroy

# Destroy with confirmation
tofu destroy

# Or auto-approve (use with caution!)
tofu destroy -auto-approve
```

---

## Support

- **Issues:** [GitHub Issues](https://github.com/syalioune/gcp-finops-sentinel/issues)
- **Discussions:** [GitHub Discussions](https://github.com/syalioune/gcp-finops-sentinel/discussions)
- **Security:** See [SECURITY.md](../SECURITY.md) for vulnerability reporting
