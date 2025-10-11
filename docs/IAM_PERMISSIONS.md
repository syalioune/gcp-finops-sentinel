# IAM Permissions Guide

Complete reference for IAM permissions required by GCP FinOps Sentinel.

## Quick Reference

| Feature | Role | Scope | Required |
|---------|------|-------|----------|
| **Project Discovery** | `roles/browser` | Organization | ✅ Yes |
| **Policy Enforcement** | `roles/orgpolicy.policyAdmin` | Organization | ✅ Yes |
| **Action Events** | `roles/pubsub.publisher` | Topic | ⚠️ Optional* |

\* Required only if `ACTION_EVENT_TOPIC` is configured

---

## Minimum Setup (Production)

### Service Account
```bash
# Create service account
gcloud iam service-accounts create finops-sentinel \
  --display-name="GCP FinOps Sentinel" \
  --project=PROJECT_ID
```

### Required Permissions
```bash
ORG_ID="123456789012"
SA_EMAIL="finops-sentinel@PROJECT_ID.iam.gserviceaccount.com"

# 1. Browser role (project discovery)
gcloud organizations add-iam-policy-binding $ORG_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/browser"

# 2. Org Policy Admin (policy enforcement)
gcloud organizations add-iam-policy-binding $ORG_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/orgpolicy.policyAdmin"

# 3. Pub/Sub Publisher (action events - optional)
gcloud pubsub topics add-iam-policy-binding TOPIC_NAME \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/pubsub.publisher"
```

---

## Permission Details

### 1. Project Discovery (`roles/browser`)

**Purpose**: Find projects by labels using Resource Manager API

**API Method**: `projects.search` (Resource Manager API v3)

**Permissions Included**:
- `resourcemanager.projects.get`
- `resourcemanager.projects.list`

**Grant Level**:
- ✅ **Organization** - Discover all projects in org
- ✅ **Folder** - Discover projects in specific folder
- ❌ **Project** - Only sees that project (limited usefulness)

**Why `roles/browser`?**
- ✅ Least-privilege for read-only access
- ✅ Standard role for resource browsing
- ⚠️ Alternatives (`roles/viewer`, `roles/resourcemanager.projectMover`) include unnecessary permissions

<details>
<summary><b>📋 Terraform Example</b></summary>

```hcl
resource "google_organization_iam_member" "finops_browser" {
  org_id = var.organization_id
  role   = "roles/browser"
  member = "serviceAccount:${google_service_account.finops_sentinel.email}"
}
```
</details>

---

### 2. Policy Enforcement (`roles/orgpolicy.policyAdmin`)

**Purpose**: Apply organization policy constraints

**API Methods**:
- `OrgPolicyClient.get_policy()`
- `OrgPolicyClient.create_policy()`
- `OrgPolicyClient.update_policy()`

**Permissions Included**:
- `orgpolicy.policy.get`
- `orgpolicy.policy.set`

**Grant Level**:
- ✅ **Organization** - Enforce across all resources
- ✅ **Folder** - Enforce on specific folders only
- ✅ **Project** - Enforce on specific projects only

**Common Constraints Applied**:
- `gcp.restrictServiceUsage` - Service restrictions
- `compute.vmExternalIpAccess` - External IP controls
- Custom constraints defined in your rules

<details>
<summary><b>📋 Terraform Example</b></summary>

```hcl
resource "google_organization_iam_member" "finops_orgpolicy" {
  org_id = var.organization_id
  role   = "roles/orgpolicy.policyAdmin"
  member = "serviceAccount:${google_service_account.finops_sentinel.email}"
}
```
</details>

---

### 3. Event Publishing (`roles/pubsub.publisher`)

**Purpose**: Publish action events for observability

**Permission**: `pubsub.topics.publish`

**Grant Level**:
- ✅ **Specific Topic** - Recommended (least-privilege)
- ⚠️ **Project** - Grants access to all topics (not recommended)

**When Required**:
- Only if `ACTION_EVENT_TOPIC` environment variable is set
- Enables audit trail and monitoring integrations

<details>
<summary><b>📋 Terraform Example</b></summary>

```hcl
resource "google_pubsub_topic_iam_member" "finops_publisher" {
  topic  = google_pubsub_topic.action_events.name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.finops_sentinel.email}"
}
```
</details>

---

## Complete Terraform Example

```hcl
# Service Account
resource "google_service_account" "finops_sentinel" {
  account_id   = "finops-sentinel"
  display_name = "GCP FinOps Sentinel"
  description  = "Service account for budget enforcement"
}

# Organization-level Browser role (project discovery)
resource "google_organization_iam_member" "finops_browser" {
  org_id = var.organization_id
  role   = "roles/browser"
  member = "serviceAccount:${google_service_account.finops_sentinel.email}"
}

# Organization-level Org Policy Admin (policy enforcement)
resource "google_organization_iam_member" "finops_orgpolicy" {
  org_id = var.organization_id
  role   = "roles/orgpolicy.policyAdmin"
  member = "serviceAccount:${google_service_account.finops_sentinel.email}"
}

# Topic-level Pub/Sub Publisher (action events - optional)
resource "google_pubsub_topic_iam_member" "finops_publisher" {
  count  = var.enable_action_events ? 1 : 0
  topic  = google_pubsub_topic.action_events[0].name
  role   = "roles/pubsub.publisher"
  member = "serviceAccount:${google_service_account.finops_sentinel.email}"
}
```

---

## Verification & Testing

### Verify Permissions

```bash
SA_EMAIL="finops-sentinel@PROJECT_ID.iam.gserviceaccount.com"

# Check organization-level permissions
gcloud organizations get-iam-policy $ORG_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:$SA_EMAIL" \
  --format="table(bindings.role)"

# Check topic-level permissions
gcloud pubsub topics get-iam-policy TOPIC_NAME \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:$SA_EMAIL"
```

### Test Project Discovery

```bash
# Impersonate service account
gcloud config set auth/impersonate_service_account $SA_EMAIL

# Test project listing
gcloud projects list --filter='labels.env=prod'

# Unset impersonation
gcloud config unset auth/impersonate_service_account
```

### Test Policy Access

```bash
# Impersonate service account
gcloud config set auth/impersonate_service_account $SA_EMAIL

# Test reading org policies
gcloud org-policies list --project=PROJECT_ID

# Unset impersonation
gcloud config unset auth/impersonate_service_account
```

### Use Debug Script

```bash
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json

python scripts/debug-project-discovery.py \
  --labels env=prod \
  --org $ORG_ID \
  --debug
```

---

## Least Privilege Best Practices

### ✅ Recommended

1. **Use organization-level roles** for production (full coverage)
2. **Grant on specific topic** for Pub/Sub (not project-wide)
3. **Separate service accounts** for dev/staging/prod
4. **Enable Cloud Audit Logs** to monitor service account activity
5. **Avoid service account keys** - Use Workload Identity where possible
6. **Test in dry-run mode** before granting production permissions

### ⚠️ Not Recommended

1. ❌ **`roles/owner` or `roles/editor`** - Way too broad
2. ❌ **Project-level `pubsub.publisher`** - Use topic-level instead
3. ❌ **Shared service accounts** across environments
4. ❌ **Long-lived service account keys** - Rotate regularly if needed

### Development/Testing Setup

For non-production environments, scope permissions tighter:

```bash
# Project-level permissions for testing
gcloud projects add-iam-policy-binding DEV_PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/browser"

gcloud projects add-iam-policy-binding DEV_PROJECT_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/orgpolicy.policyAdmin"
```

---

## Troubleshooting

### ❌ Permission Denied Errors

**Error**: `The caller does not have permission`

**Solutions**:
1. ✅ Verify role granted at correct scope (org/folder/project)
2. ✅ Wait 60-120 seconds for IAM propagation
3. ✅ Confirm Cloud Run uses correct service account
4. ✅ Check organization policies don't restrict service account

**Debug Commands**:
```bash
# Verify service account in Cloud Run
gcloud run services describe gcp-finops-sentinel \
  --region=REGION \
  --format="value(spec.template.spec.serviceAccountName)"

# Check all bindings for service account
gcloud organizations get-iam-policy $ORG_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:$SA_EMAIL"
```

### ❌ Project Discovery Returns 0 Projects

**Possible Causes**:
1. ❌ Missing `roles/browser` at org/folder level
2. ❌ Labels don't match or don't exist
3. ❌ Projects are not ACTIVE (deleted/pending deletion)
4. ❌ Query syntax error in label filter

**Debug Steps**:
```bash
# 1. Verify labels exist on projects
gcloud projects list --filter='labels.env=prod'

# 2. Check service account permissions
gcloud organizations get-iam-policy $ORG_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:$SA_EMAIL"

# 3. Use debug script with comparison
python scripts/debug-project-discovery.py \
  --labels env=prod \
  --compare-gcloud
```

### ❌ Policies Not Applying

**Checklist**:
- [ ] `DRY_RUN=false` (check environment variable)
- [ ] Service account has `roles/orgpolicy.policyAdmin`
- [ ] No conflicting organization policies
- [ ] Rule conditions match budget alert data
- [ ] Resource IDs are correct (project/folder/org)

**Debug**:
```bash
# Check applied policies
gcloud org-policies list --project=PROJECT_ID

# Check specific constraint
gcloud org-policies describe gcp.restrictServiceUsage \
  --project=PROJECT_ID
```

---

## IAM Propagation

**Important**: IAM changes take time to propagate

| Change Type | Propagation Time |
|-------------|------------------|
| Grant new role | 60-120 seconds |
| Revoke role | 60-120 seconds |
| Policy changes | Up to 7 minutes |

**Best Practice**: Wait 2 minutes after IAM changes before testing

---

## Security Considerations

### Audit Logging

Enable Cloud Audit Logs for organization policy changes:

```bash
# Review org policy changes
gcloud logging read "protoPayload.serviceName=orgpolicy.googleapis.com" \
  --limit=50 \
  --format=json
```

### Service Account Monitoring

Monitor service account activity:

```bash
# View service account activity
gcloud logging read "protoPayload.authenticationInfo.principalEmail=$SA_EMAIL" \
  --limit=50
```

### Separation of Duties

| Environment | Service Account | Scope |
|-------------|----------------|-------|
| **Development** | `finops-sentinel-dev@...` | Project-level only |
| **Staging** | `finops-sentinel-staging@...` | Folder-level |
| **Production** | `finops-sentinel-prod@...` | Organization-level |

---

## Additional Resources

- [Resource Manager API - projects.search](https://cloud.google.com/resource-manager/reference/rest/v3/projects/search)
- [Organization Policy API](https://cloud.google.com/resource-manager/docs/organization-policy/overview)
- [IAM Roles Reference](https://cloud.google.com/iam/docs/understanding-roles)
- [Service Account Best Practices](https://cloud.google.com/iam/docs/best-practices-service-accounts)
- [Workload Identity Federation](https://cloud.google.com/iam/docs/workload-identity-federation)

---

## Summary

**Minimum Required Permissions**:
```
Organization Level:
  ├── roles/browser (project discovery)
  └── roles/orgpolicy.policyAdmin (policy enforcement)

Topic Level (optional):
  └── roles/pubsub.publisher (action events)
```

**Setup Time**: ~5 minutes
**IAM Propagation**: Wait 2 minutes after granting
**Verification**: Use `gcloud organizations get-iam-policy` or debug scripts

---

**Last Updated**: 2025-10-23
