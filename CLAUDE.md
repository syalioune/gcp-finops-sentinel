# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**GCP FinOps Sentinel** is a Cloud Run service that automatically enforces organization policies in response to budget alerts. When budget thresholds are exceeded, the service applies configured policy actions (service restrictions, constraints) to control costs.

**Technology Stack**: Python 3.13, Functions Framework (for Cloud Run), GCP Organization Policy API, GCP Resource Manager API, Docker, Pub/Sub

## Essential Commands

### Testing
```bash
# Run all tests (unit + integration)
./scripts/run-tests.sh all

# Unit tests only
./scripts/run-tests.sh unit

# Integration tests only (requires Docker Compose)
./scripts/run-tests.sh integration

# Generate coverage report
./scripts/run-tests.sh coverage
```

### Local Development
```bash
# Start local environment with Pub/Sub emulator, MailHog, and budget function
docker compose up -d

# View function logs
docker compose logs -f budget-function

# Test email templates (view at http://localhost:8025)
docker compose exec budget-function python /workspace/../scripts/test-email-templates.py

# Or run locally
python scripts/test-email-templates.py

# Publish test event to emulator
export PUBSUB_EMULATOR_HOST=localhost:8681
python scripts/publish-budget-alert-event.py

# Stop environment
docker compose down

# Run function locally (without Docker)
cd src
export DRY_RUN=true
export ORGANIZATION_ID=123456789012
export RULES_CONFIG_PATH=../test-data/test-rules.json  # or test-rules.yaml
export SMTP_HOST=localhost
export SMTP_PORT=1025
export TEMPLATE_DIR=../email-templates
functions-framework --target=budget_response_handler --debug
```

**MailHog Email Testing**:
- Web UI: http://localhost:8025
- SMTP Server: localhost:1025
- Use `scripts/test-email-templates.py` to preview email templates

### Code Quality
```bash
# Format code
cd src
black .
isort .

# Lint code (maintain score above 8.0)
pylint *.py
```

### Docker
```bash
# Build image locally
docker build -t gcp-finops-sentinel:local .

# Run container locally
docker run -p 8080:8080 \
  -e ORGANIZATION_ID=123456789012 \
  -e RULES_CONFIG='{"rules":[]}' \
  gcp-finops-sentinel:local
```

## Architecture

### Core Components

1. **RuleEngine** ([src/rule_engine.py](src/rule_engine.py))
   - Evaluates budget alert data against configured rules
   - Supports threshold-based conditions with multiple operators: `>=`, `>`, `==`, `<`, `<=`, `min`, `max`
   - Supports single conditions or arrays of conditions for range-based matching
   - Implements project filtering (exact match, list match, wildcard patterns)
   - Returns list of actions to execute

2. **BudgetResponseEngine** ([src/budget_response_engine.py](src/budget_response_engine.py))
   - Executes policy actions on GCP resources (projects, folders, or organizations)
   - Applies service restrictions via `gcp.restrictServiceUsage` constraint
   - Applies custom organization policy constraints
   - Supports hierarchical targeting (project, folder, organization level)
   - Publishes action events to optional Pub/Sub topic for observability
   - Supports dry-run mode via `DRY_RUN` environment variable to log actions without executing them

3. **Configuration Loading** ([src/config.py](src/config.py))
   - `load_rules_config()` function loads rules from environment or file
   - Supports `RULES_CONFIG` (JSON or YAML string) or `RULES_CONFIG_PATH` (file path)
   - Accepts both JSON and YAML formats in environment variable and files
   - For environment variable: tries JSON first, then falls back to YAML
   - For files: format determined by file extension (.json, .yml, .yaml)
   - Returns validated configuration dictionary

4. **ProjectDiscovery** ([src/project_discovery.py](src/project_discovery.py))
   - Discovers projects based on label filters using Resource Manager API v3
   - **Returns display names**: Each project includes both `project_id` and `display_name` for improved readability
   - **Fixed**: Correct query syntax `labels.key:value` (colon per API docs)
   - **Fixed**: Correct organization parent format `parent:organizations/ORG_ID`
   - **Fixed**: Post-filters results for AND logic (API uses OR for multiple labels)
   - Only returns ACTIVE projects (matching gcloud default behavior)
   - Supports scoping searches to specific organization
   - Enables dynamic project targeting without hardcoding project IDs
   - Supports dry-run mode for testing
   - Use `scripts/debug-project-discovery.py` to troubleshoot label discovery issues

5. **EmailService** ([src/email_service.py](src/email_service.py))
   - Sends HTML email notifications via SMTP with Jinja2 templating
   - Auto-loads templates from `email-templates/` directory (no embedded templates)
   - Professional, mobile-responsive templates with severity-based color coding
   - Configurable SMTP server with TLS support
   - Override template directory via `TEMPLATE_DIR` environment variable
   - Supports dry-run mode for testing email generation without sending

6. **budget_response_handler** ([src/handler.py](src/handler.py))
   - Cloud Run entry point (CloudEvent trigger via Eventarc)
   - Decodes Pub/Sub messages containing budget alert data
   - **Fetches human-readable names**: Retrieves display names for billing accounts, budgets, and projects
   - Resolves action targets (projects, folders, organization, label-based discovery)
   - Orchestrates rule evaluation and action execution
   - Comprehensive error handling and logging

7. **Main Entry Point** ([src/main.py](src/main.py))
   - Simple entry point that imports and exposes the handler
   - Configures logging for the application

### Data Flow

```
Budget Alert → Pub/Sub Topic → Eventarc Trigger → Cloud Run Service
                                                          ↓
                                        Parse message & extract data
                                                          ↓
                                        RuleEngine.evaluate(budget_data)
                                                          ↓
                                        Match conditions (threshold, project)
                                                          ↓
                                        Return actions list
                                                          ↓
                                        BudgetResponseEngine executes actions
                                                          ↓
                                        Apply org policies via OrgPolicyClient
                                                          ↓
                                        Publish action event to Pub/Sub (if configured)
```

### Dry-Run Mode

For local development and testing, the function supports **dry-run mode**:
- Set `DRY_RUN=true` environment variable to enable
- Actions are logged but not executed (no real GCP API calls)
- Action events are still published to Pub/Sub if `ACTION_EVENT_TOPIC` is configured
- Useful for testing rule logic without affecting real GCP resources
- Integration tests use dry-run mode with Pub/Sub emulator to verify complete flow

## Configuration

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `ORGANIZATION_ID` | GCP Organization ID (required) | - |
| `RULES_CONFIG` | Rules as JSON or YAML string | - |
| `RULES_CONFIG_PATH` | Path to rules config file (JSON or YAML) | `/workspace/rules.json` |
| `ACTION_EVENT_TOPIC` | Pub/Sub topic for publishing action events (optional) | - |
| `DRY_RUN` | Enable dry-run mode (log actions without executing) | `false` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `PUBSUB_EMULATOR_HOST` | Pub/Sub emulator address for local testing | - |
| `SMTP_HOST` | SMTP server hostname for email notifications | - |
| `SMTP_PORT` | SMTP server port | `587` (TLS) / `25` (non-TLS) |
| `SMTP_USE_TLS` | Enable STARTTLS for SMTP connection | `true` |
| `SMTP_USER` | SMTP authentication username | - |
| `SMTP_PASSWORD` | SMTP authentication password | - |
| `SMTP_FROM_EMAIL` | Default sender email address | `SMTP_USER` |
| `TEMPLATE_DIR` | Path to custom Jinja2 email templates directory | - |

### Rules Configuration

Rules can be defined in JSON or YAML format. See [test-data/test-rules.json](test-data/test-rules.json) and [test-data/test-rules.yaml](test-data/test-rules.yaml) for examples.

**Rule Structure**:
- **conditions**: `threshold_percent` (operator, value), optional `billing_account_filter`, optional `budget_id_filter`
- **actions**: List of actions (restrict_services, apply_constraint, log_only)
- **targeting**: Actions support `target_projects`, `target_folders`, `target_organization`, or `target_labels` for resource selection

**Threshold Operators**:
The `threshold_percent` condition supports the following operators:
- **Standard operators**: `>=`, `>`, `==`, `<`, `<=`
- **Range operators**: `min` (inclusive lower bound, equivalent to `>=`), `max` (inclusive upper bound, equivalent to `<=`)
- **Single condition**: `{"operator": ">=", "value": 100}`
- **Array of conditions** (all must match): `[{"operator": "min", "value": 80}, {"operator": "max", "value": 89.99}]`

**Example threshold configurations**:
```json
// Simple threshold (100% or higher)
"threshold_percent": {"operator": ">=", "value": 100}

// Range using min/max operators (80-89.99%)
"threshold_percent": [
  {"operator": "min", "value": 80},
  {"operator": "max", "value": 89.99}
]

// Open-ended range (115% or higher)
"threshold_percent": {"operator": "min", "value": 115}
```

**Action Types**:
- `restrict_services`: Deny specific GCP services via `gcp.restrictServiceUsage`
- `apply_constraint`: Apply custom org policy constraints (boolean or list-based)
- `log_only`: Log without taking action
- `send_mail`: Send email notification via configured SMTP server (see Email Notifications section)

### Policy Action Event Publishing

When `ACTION_EVENT_TOPIC` is configured, the service publishes structured event messages to the specified Pub/Sub topic after each action execution. This enables:
- **Observability**: Monitor all enforcement actions in real-time
- **Auditing**: Maintain a complete history of policy changes
- **Integration**: Trigger downstream workflows (notifications, ticketing, analytics)

**Event Message Structure**:
```json
{
  "timestamp": 1234567890.123,
  "action_type": "restrict_services",
  "resource_id": "my-project-123",
  "resource_type": "project",
  "success": true,
  "organization_id": "123456789012",
  "details": {
    "constraint": "gcp.restrictServiceUsage",
    "action": "deny",
    "services": ["compute.googleapis.com"],
    "display_name": "My Production Project",
    "error": null
  }
}
```

**Display Names**: Policy action events now include human-readable `display_name` in the details for improved observability and reporting.

**Event Types**:
- `restrict_services`: Service restriction applied
- `apply_constraint`: Custom constraint applied
- `send_email`: Email notification sent

Events are published regardless of action success/failure. Failed actions include error details in the `details.error` field.

**Setup**:
1. Create a Pub/Sub topic for policy action events (e.g., `policy-action-events`)
2. Set `ACTION_EVENT_TOPIC=projects/{project_id}/topics/{topic_id}` environment variable
3. Grant Cloud Run service account `pubsub.publisher` role on the topic
4. Subscribe to the topic to consume events (push/pull subscription)

### Email Notifications

The service supports sending HTML email notifications for budget alerts using configured SMTP servers with Jinja2 templating.

**Features**:
- **External Templates**: Professional, mobile-responsive HTML templates stored in `email-templates/` folder
- **Template Auto-Loading**: EmailService automatically loads templates from `../email-templates` relative to src/ directory
- **Custom Templates**: Full support for custom Jinja2 templates by editing files in `email-templates/`
- **SMTP Configuration**: Flexible SMTP settings with TLS support
- **Dry-Run Mode**: Test email generation without sending

**send_mail Action Configuration**:
```json
{
  "type": "send_mail",
  "to_emails": ["admin@example.com", "finops-team@example.com"],
  "template": "budget_alert",
  "custom_message": "Immediate attention required"
}
```

**Action Parameters**:
- `to_emails` (required): List of recipient email addresses
- `template` (optional): Template name (`budget_alert` or `policy_action`), defaults to `budget_alert`
- `custom_message` (optional): Custom message to include in email body

**Built-in Templates**:
- `budget_alert`: Professional email with budget metrics, threshold information, and automated actions taken
- `policy_action`: Email notification for individual policy action events (when subscribed to ACTION_EVENT_TOPIC)

**Example Rule with Email Notification**:
```json
{
  "name": "critical_budget_alert",
  "conditions": {
    "threshold_percent": {"operator": ">=", "value": 100}
  },
  "actions": [
    {
      "type": "restrict_services",
      "target_projects": ["prod-project-1"],
      "services": ["compute.googleapis.com"]
    },
    {
      "type": "send_mail",
      "to_emails": ["sre-team@example.com", "finance@example.com"],
      "template": "budget_alert",
      "custom_message": "CRITICAL: Budget exceeded. Compute services restricted."
    }
  ]
}
```

**SMTP Setup**:
1. Configure SMTP environment variables (see Environment Variables table)
2. For Gmail: Use App Passwords (not regular password)
3. For SendGrid: Use API key as password with username `apikey`
4. For AWS SES: Configure SMTP credentials from SES console
5. Test in dry-run mode first: `DRY_RUN=true`

**Email Template Variables**:
Budget alert template receives:
- `cost_amount`, `budget_amount`, `threshold_percent`
- `billing_account_id`, `billing_account_name` (human-readable name)
- `budget_id`, `budget_name` (human-readable name)
- `organization_id`
- `actions` (list of automated actions taken, includes `display_name` for projects)
- `custom_message` (optional custom message)

**Display Names in Emails**: Email templates automatically show human-readable names with IDs in smaller text for better readability:
- Billing Account: "Production Account" (012345-6789AB-CDEF01)
- Budget: "2025 Q1 Budget" (budget-uuid)
- Project Actions: "My Project (my-project-123)"

**Email Templates**:
All email templates are stored externally in [email-templates/](email-templates/):
- **budget_alert.html**: Mobile-responsive budget alert with color-coded severity levels
- **budget_alert_subject.txt**: Dynamic subject line template
- **policy_action.html**: Policy action event notification template
- **policy_action_subject.txt**: Policy action subject line template
- See [email-templates/README.md](email-templates/README.md) for customization guide

**Template System**:
1. Templates are automatically loaded from `email-templates/` directory (relative to src/)
2. No embedded templates - all templates are external files
3. Override default location with `TEMPLATE_DIR` environment variable
4. Templates use Jinja2 syntax with full access to context variables
5. Test templates with `scripts/test-email-templates.py` and view in MailHog (http://localhost:8025)

## Project Structure

```
src/
├── main.py                    # Entry point, exposes handler
├── handler.py                 # Cloud Run handler
├── budget_response_engine.py  # Policy enforcement engine
├── rule_engine.py             # Rule evaluation logic
├── project_discovery.py       # Label-based project discovery
├── email_service.py           # Email notification service with Jinja2 templates
├── config.py                  # Configuration loading
├── requirements.txt           # Production dependencies
└── requirements-test.txt      # Test dependencies

tests/
├── __init__.py                       # Test package init
├── conftest.py                       # Pytest configuration
├── test_budget_response_engine.py    # BudgetResponseEngine tests
├── test_rule_engine.py               # RuleEngine tests
├── test_config.py                    # Configuration loading tests
├── test_project_discovery.py         # ProjectDiscovery tests
├── test_email_service.py             # EmailService tests
└── test_handler.py                   # Handler integration tests

integration-tests/
└── run_integration_tests.py  # End-to-end tests with Pub/Sub emulator

test-data/
├── test-rules.json      # Example rules for testing (JSON format)
└── test-rules.yaml      # Example rules for testing (YAML format)

scripts/
├── run-tests.sh                        # Test runner (bash)
├── publish-budget-alert-event.py       # Publish test budget alerts (Python)
├── consume-policy-action-events.py     # Consume action events (Python)
├── test-email-templates.py             # Test email templates with MailHog (Python)
└── debug-project-discovery.py          # Debug label-based project discovery (Python)

email-templates/
├── README.md                   # Template customization guide
├── budget_alert.html           # Custom budget alert template
├── budget_alert_subject.txt    # Budget alert subject line
├── policy_action.html          # Custom policy action template
└── policy_action_subject.txt   # Policy action subject line

Dockerfile               # Container image for Cloud Run
Dockerfile.test          # Container for running tests
docker-compose.yml       # Local dev environment (service + Pub/Sub emulator)
```

## Development Practices

### Code Style
- **PEP 8** compliance, line length 100 characters
- Use **Black** for formatting, **isort** for imports
- Add type hints for function parameters and returns
- Use Google-style docstrings for classes and functions
- Maintain **pylint** score above 8.0

### Testing Requirements
- Write unit tests for all new functionality in `tests/` directory
- Use mocks for GCP API calls (see [src/mocks.py](src/mocks.py))
- Run integration tests to verify end-to-end flow
- Integration tests include:
  - Budget threshold enforcement tests
  - Policy action verification via Pub/Sub event subscription
  - **Email notification tests** (verifies emails sent to MailHog)
  - Email content validation (subject, recipients, body)
  - Email with prior actions included in body
  - **Email action event publishing** (verifies send_email events in Pub/Sub)
    - Action type: `send_email`
    - Resource type: `notification`
    - Resource ID: `email`
    - Details: `template`, `recipients` (list), `error` (if any)
- Maintain test coverage above 80%
- Test edge cases: threshold boundaries, missing data, invalid configs

### Commit Conventions
Use [Conventional Commits](https://www.conventionalcommits.org/):
- `feat:` for new features
- `fix:` for bug fixes
- `test:` for test additions/updates
- `docs:` for documentation changes
- `refactor:` for code restructuring

## Deployment

This is typically deployed via infrastructure-as-code (Terraform/OpenTofu). The GitHub Actions workflow:
1. Runs unit tests
2. Builds Docker image
3. Pushes to Artifact Registry

Deployment is handled externally via IaC modules that reference the container image.

### IAM Permissions

The Cloud Run service account requires specific IAM roles. See **[docs/IAM_PERMISSIONS.md](docs/IAM_PERMISSIONS.md)** for detailed setup.

**Quick Summary**:
- **`roles/browser`** (Organization level) - For project discovery by labels
- **`roles/orgpolicy.policyAdmin`** (Organization level) - For policy enforcement
- **`roles/pubsub.publisher`** (Topic level) - For publishing action events

**Example**:
```bash
# Grant Browser role for project discovery
gcloud organizations add-iam-policy-binding $ORG_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/browser"

# Grant Org Policy Admin for enforcement
gcloud organizations add-iam-policy-binding $ORG_ID \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/orgpolicy.policyAdmin"
```

See [docs/IAM_PERMISSIONS.md](docs/IAM_PERMISSIONS.md) for complete Terraform examples and troubleshooting.

## Debugging Tips

### View Logs in Docker Compose
```bash
docker compose logs -f budget-function  # Function logs
docker compose logs -f pubsub-emulator  # Pub/Sub emulator logs
docker compose logs -f mailhog          # MailHog logs
```

### Test Email Templates
```bash
# Send sample emails to MailHog
python scripts/test-email-templates.py

# Or from within Docker
docker compose exec budget-function python /workspace/../scripts/test-email-templates.py

# View emails in browser
open http://localhost:8025
```

### Test Specific Scenarios
Modify [test-data/test-rules.json](test-data/test-rules.json) and restart:
```bash
docker compose restart budget-function
```

### Interactive Python Shell
```bash
docker compose exec budget-function python3
>>> from main import RuleEngine
>>> # Test your logic interactively
```

### Debug Project Discovery by Labels
```bash
# Test label-based project discovery
python scripts/debug-project-discovery.py --labels env=prod team=backend

# Test with organization scope
python scripts/debug-project-discovery.py --labels env=prod --org 123456789012

# Compare with gcloud results
python scripts/debug-project-discovery.py --labels env=prod --compare-gcloud

# Enable debug logging
python scripts/debug-project-discovery.py --labels env=prod --debug
```

### Common Issues
- **Function not receiving messages**: Check that `PUBSUB_EMULATOR_HOST` is set correctly
- **Mock not activating**: Ensure `USE_MOCKS=true` is set
- **Tests failing**: Rebuild containers with `docker compose build --no-cache`
- **Project discovery returns 0 projects**:
  - Verify labels exist on projects: `gcloud projects list --filter='labels.env=prod'`
  - Check IAM permissions: requires `resourcemanager.projects.list`
  - Use debug script: `python scripts/debug-project-discovery.py --labels env=prod --compare-gcloud`
  - Ensure projects are ACTIVE (not deleted/pending deletion)

## Key Files to Understand

1. **Core Modules** (start here):
   - [src/handler.py](src/handler.py) - Cloud Run entry point
   - [src/rule_engine.py](src/rule_engine.py) - Rule evaluation logic
   - [src/budget_response_engine.py](src/budget_response_engine.py) - Policy enforcement
   - [src/email_service.py](src/email_service.py) - Email notification service
   - [src/config.py](src/config.py) - Configuration loading

2. **Configuration**:
   - [test-data/test-rules.json](test-data/test-rules.json) - Example rules

3. **Tests** (well-organized by module):
   - [tests/test_rule_engine.py](tests/test_rule_engine.py) - Rule evaluation tests
   - [tests/test_budget_response_engine.py](tests/test_budget_response_engine.py) - Policy action tests
   - [tests/test_email_service.py](tests/test_email_service.py) - Email service tests
   - [tests/test_config.py](tests/test_config.py) - Config loading tests
   - [tests/test_handler.py](tests/test_handler.py) - Integration tests

4. **Development**:
   - [docker-compose.yml](docker-compose.yml) - Local development setup
   - [LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md) - Detailed local dev guide
