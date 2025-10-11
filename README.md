# 💸 GCP FinOps Sentinel

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Tests](https://github.com/syalioune/gcp-finops-sentinel/actions/workflows/test.yml/badge.svg)](https://github.com/syalioune/gcp-finops-sentinel/actions/workflows/test.yml)
![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Status](https://img.shields.io/badge/status-active-success)

![Python](https://img.shields.io/badge/python-3.13-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Google Cloud](https://img.shields.io/badge/GoogleCloud-%234285F4.svg?style=for-the-badge&logo=google-cloud&logoColor=white)
![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/github%20actions-%232671E5.svg?style=for-the-badge&logo=githubactions&logoColor=white)

**Automated GCP cost control through policy enforcement.** Event-driven Cloud Run service that automatically enforces organization policies when budget thresholds are exceeded, helping you control cloud costs without manual intervention.

---

## ✨ Features

* 🚨 **Event-Driven**: Triggered automatically by GCP Budget Alerts via Pub/Sub
* 📊 **Flexible Rules Engine**: Configure multiple rules with threshold-based conditions (>=, >, ==, <, <=, min, max)
* 🎯 **Multi-Target Support**: Apply policies to projects, folders, organizations, or discover projects by labels
* 🔒 **Policy Enforcement**: Restrict GCP services and apply organization policy constraints
* 📧 **Email Notifications**: HTML email alerts via SMTP with customizable Jinja2 templates
* 📡 **Observability**: Optional Pub/Sub event publishing for auditing and monitoring
* 🏗️ **Infrastructure as Code**: Deploy with OpenTofu/Terraform using Docker container
* 🧪 **Well-Tested**: 80%+ test coverage with unit and integration tests
* 🐳 **Container-Based**: Cloud Run deployment for serverless scalability
* 🔬 **Local Development**: Docker Compose environment with Pub/Sub and MailHog emulators

---

## 🚀 Quick Start

### Deploy to Production (5 Minutes)

```bash
# 1. Clone repository
git clone https://github.com/syalioune/gcp-finops-sentinel.git
cd gcp-finops-sentinel/tofu

# 2. Configure deployment
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars: project_id, organization_id, region, rules

# 3. Deploy
tofu init && tofu apply
```

**Done!** Cloud Run service deployed with monitoring, secrets, and IAM configured.

📖 **Detailed guide**: [docs/TOFU_DEPLOYMENT.md](docs/TOFU_DEPLOYMENT.md)

### Test Locally (2 Minutes)

```bash
# Start local environment with Pub/Sub emulator + MailHog
docker compose up -d

# Publish test budget alert (120% threshold)
export PUBSUB_EMULATOR_HOST=localhost:8681
python scripts/publish-budget-alert-event.py --cost-amount 1200 --budget-amount 1000

# View logs and email notifications
docker compose logs -f budget-function
# Open http://localhost:8025 for email testing
```

📖 **Detailed guide**: [docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md)

---

## 🏗️ Architecture

![gcp_finops_sentinel](./diagrams/gcp_finops_sentinel.png)

<details>
<summary><b>📊 Components & Data flow</b> (click to expand)</summary>

**Components:**
1. **GCP Budget** → Configured with threshold rules and Pub/Sub notifications
2. **Budget Alerts Topic** → Receives budget alert messages
3. **Eventarc Trigger** → Routes Pub/Sub messages to Cloud Run
4. **Cloud Run Service** → Processes alerts, evaluates rules, applies policies
5. **Rule Engine** → Evaluates budget data against configured rules
6. **Policy Engine** → Executes policy actions (restrict services, apply constraints)
7. **Email Service** → Sends HTML notifications via SMTP
8. **Action Events Topic** → (Optional) Publishes audit events
9. **Target Resources** → Projects/folders/organizations where policies are enforced

**Data Flow:**
```
Budget Alert → Pub/Sub → Eventarc → Cloud Run → Rule Engine → Policy Engine → GCP Org Policy API
                                         ↓              ↓
                                   Email Service   Action Events
```

</details>

---

## ⚙️ Configuration

### Rules Configuration

Rules define **when** and **what** actions to take based on budget thresholds.

<details>
<summary><b>📝 Rule Structure Example</b> (JSON/YAML supported)</summary>

```yaml
rules:
  - name: critical_budget_breach
    description: Restrict compute when budget exceeds 100%
    conditions:
      threshold_percent:
        operator: ">="
        value: 100
      billing_account_filter: "012345-6789AB-CDEF01"  # Optional
      budget_id_filter: "budget-uuid"  # Optional
    actions:
      # Restrict services on specific projects
      - type: restrict_services
        target_projects:
          - prod-web-1
          - prod-api-1
        services:
          - compute.googleapis.com

      # Target projects by labels (dynamic discovery)
      - type: restrict_services
        target_labels:
          env: prod
          cost-center: engineering
        services:
          - compute.googleapis.com

      # Apply constraint on folder
      - type: apply_constraint
        target_folders:
          - "123456789012"
        constraint: compute.vmExternalIpAccess
        enforce: true

      # Send email notification
      - type: send_mail
        to_emails:
          - finops-team@example.com
        template: budget_alert
        custom_message: "Critical budget breach!"
```

**Examples:** [test-data/test-rules.json](test-data/test-rules.json), [test-data/test-rules.yaml](test-data/test-rules.yaml)

</details>

<details>
<summary><b>🎯 Threshold Operators</b></summary>

| Operator | Description | Example |
|----------|-------------|---------|
| `>=` | Greater than or equal | `{"operator": ">=", "value": 100}` |
| `>` | Greater than | `{"operator": ">", "value": 90}` |
| `==` | Equals | `{"operator": "==", "value": 100}` |
| `<` | Less than | `{"operator": "<", "value": 50}` |
| `<=` | Less than or equal | `{"operator": "<=", "value": 25}` |
| `min` | Minimum (inclusive) | `{"operator": "min", "value": 80}` |
| `max` | Maximum (inclusive) | `{"operator": "max", "value": 89.99}` |

**Range matching** (all conditions must match):
```json
"threshold_percent": [
  {"operator": "min", "value": 80},
  {"operator": "max", "value": 89.99}
]
```

</details>

<details>
<summary><b>🎬 Action Types</b></summary>

| Action | Description | Required Parameters |
|--------|-------------|---------------------|
| `restrict_services` | Deny specific GCP services via `gcp.restrictServiceUsage` | `services`, targeting* |
| `apply_constraint` | Apply custom org policy constraint | `constraint`, `enforce`, targeting* |
| `send_mail` | Send HTML email via SMTP | `to_emails`, optional `template` |
| `log_only` | Log without taking action | `message`, targeting* |

**\*Targeting Methods** (choose at least one):
- `target_projects`: List of project IDs
- `target_folders`: List of folder IDs
- `target_organization`: Organization ID
- `target_labels`: Label key-value pairs for dynamic project discovery

</details>

<details>
<summary><b>🔐 Environment Variables</b></summary>

| Variable | Purpose | Required | Default |
|----------|---------|----------|---------|
| `ORGANIZATION_ID` | GCP Organization ID | ✅ Yes | - |
| `RULES_CONFIG` | Rules as JSON/YAML string | ⚠️ Or RULES_CONFIG_PATH | - |
| `RULES_CONFIG_PATH` | Path to rules file | ⚠️ Or RULES_CONFIG | `/workspace/rules.json` |
| `ACTION_EVENT_TOPIC` | Pub/Sub topic for action events | ❌ No | - |
| `DRY_RUN` | Log without executing | ❌ No | `false` |
| `LOG_LEVEL` | Logging verbosity | ❌ No | `INFO` |
| `SMTP_HOST` | SMTP server hostname | ⚠️ If using `send_mail` | - |
| `SMTP_PORT` | SMTP server port | ⚠️ If using `send_mail` | `587` |
| `SMTP_USER` | SMTP username | ⚠️ If using `send_mail` | - |
| `SMTP_PASSWORD` | SMTP password | ⚠️ If using `send_mail` | - |
| `SMTP_USE_TLS` | Enable STARTTLS | ❌ No | `true` |
| `SMTP_FROM_EMAIL` | Sender email | ❌ No | `$SMTP_USER` |
| `TEMPLATE_DIR` | Custom templates directory | ❌ No | `/workspace/email-templates` |

</details>

---

## 🚢 Deployment

GCP FinOps Sentinel is deployed as a **Cloud Run service** using container images. The production-ready OpenTofu module handles all infrastructure provisioning.

### Prerequisites

| Requirement | Version | Purpose |
|-------------|---------|---------|
| **GCP Organization** | - | Must have billing enabled |
| **OpenTofu/Terraform** | ≥ 1.6 / ≥ 1.0 | Infrastructure provisioning |
| **Docker** | Latest | Container images & local dev |
| **gcloud CLI** | Latest | GCP authentication & API enablement |

### Deployment Options

| Method | Use Case | Guide |
|--------|----------|-------|
| **OpenTofu Module** | Production deployment (recommended) | [docs/TOFU_DEPLOYMENT.md](docs/TOFU_DEPLOYMENT.md) |
| **Manual Terraform** | Custom deployments | [tofu/](tofu/) example |
| **Pre-built Images** | Quick testing | `docker pull syalioune/gcp-finops-sentinel:latest` |

### IAM Requirements

The Cloud Run service account requires:
- ✅ `roles/browser` (Organization level) - For project discovery
- ✅ `roles/orgpolicy.policyAdmin` (Organization level) - For policy enforcement
- ⚠️ `roles/pubsub.publisher` (Topic level) - For action events (optional)

📖 **Complete IAM guide**: [docs/IAM_PERMISSIONS.md](docs/IAM_PERMISSIONS.md)

---

## 🔬 Development

### Local Development Environment

```bash
# Start all services (Pub/Sub emulator, MailHog, Cloud Run function)
docker compose up -d

# View function logs
docker compose logs -f budget-function

# Test email templates (view at http://localhost:8025)
python scripts/test-email-templates.py

# Publish test events
export PUBSUB_EMULATOR_HOST=localhost:8681
python scripts/publish-budget-alert-event.py

# Stop environment
docker compose down
```

**Services:**
- Budget Function: http://localhost:8080
- MailHog Web UI: http://localhost:8025
- Pub/Sub Emulator: localhost:8681

### Code Quality Tools

```bash
# Format code
cd src && black . && isort .

# Lint code (maintain score > 8.0)
pylint *.py

# Type checking
mypy *.py
```

### Testing

```bash
# Run all tests (unit + integration)
./scripts/run-tests.sh all

# Unit tests only
pytest tests/ -v --cov=src

# Integration tests (requires Docker Compose)
./scripts/run-tests.sh integration

# Coverage report
pytest tests/ -v --cov=src --cov-report=html
# Open htmlcov/index.html
```

📖 **Detailed development guide**: [docs/LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md)

---

## 📊 Observability

### Cloud Logging

View Cloud Run logs in GCP Console or via gcloud:

```bash
# View all function logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=gcp-finops-sentinel" --limit=50

# Filter by action type
gcloud logging read "jsonPayload.action_type=restrict_services" --limit=20

# View failures only
gcloud logging read "jsonPayload.success=false OR severity>=ERROR" --limit=20
```

### Action Events (Optional)

When `ACTION_EVENT_TOPIC` is configured, every policy action publishes a structured event:

```json
{
  "timestamp": 1234567890.123,
  "action_type": "restrict_services",
  "project_id": "my-project-123",
  "success": true,
  "organization_id": "123456789012",
  "details": {
    "constraint": "gcp.restrictServiceUsage",
    "services": ["compute.googleapis.com"],
    "error": null
  }
}
```

**Use cases:**
- Real-time monitoring dashboards
- BigQuery audit trail
- SIEM integration
- Ticketing system automation

---

## 🤝 Contributing

Contributions welcome! Please follow these guidelines:

### Quick Start

```bash
# 1. Fork & clone
git clone https://github.com/YOUR_USERNAME/gcp-finops-sentinel.git
cd gcp-finops-sentinel

# 2. Install dependencies
pip install -r src/requirements.txt -r src/requirements-test.txt

# 3. Install pre-commit hooks
pre-commit install && pre-commit install --hook-type commit-msg

# 4. Create feature branch
git checkout -b feat/my-feature

# 5. Make changes & test
pytest tests/ -v
black src/ tests/ && isort src/ tests/
pylint src/ tests/  # Score must be > 8.0

# 6. Commit using Conventional Commits
git commit -m "feat: add awesome feature"

# 7. Push & create PR
git push origin feat/my-feature
```

### Code Standards

- ✅ **PEP 8** compliance (100 char line length)
- ✅ **Black** for formatting, **isort** for imports
- ✅ **Type hints** for functions
- ✅ **Google-style docstrings**
- ✅ **Pylint score** > 8.0
- ✅ **Test coverage** > 80%

### Commit Convention

| Prefix | Purpose | Example |
|--------|---------|---------|
| `feat:` | New feature | `feat: add Slack notifications` |
| `fix:` | Bug fix | `fix: handle missing budget_id` |
| `docs:` | Documentation | `docs: update IAM guide` |
| `test:` | Tests | `test: add email service tests` |
| `refactor:` | Code restructuring | `refactor: simplify rule matching` |

📖 **Full guidelines**: [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [TOFU_DEPLOYMENT.md](docs/TOFU_DEPLOYMENT.md) | Complete OpenTofu/Terraform deployment guide |
| [IAM_PERMISSIONS.md](docs/IAM_PERMISSIONS.md) | Required IAM roles and troubleshooting |
| [LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md) | Local development environment setup |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Contribution guidelines and standards |
| [SECURITY.md](SECURITY.md) | Security policy and vulnerability reporting |
| [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) | Community standards |
| [CHANGELOG.md](CHANGELOG.md) | Version history and release notes |

---

## 🗂️ Project Structure

```
gcp-finops-sentinel/
├── src/                          # Source code
│   ├── main.py                   # Entry point
│   ├── handler.py                # Cloud Run event handler
│   ├── budget_response_engine.py # Policy enforcement
│   ├── rule_engine.py            # Rule evaluation
│   ├── project_discovery.py      # Label-based discovery
│   ├── email_service.py          # SMTP email notifications
│   └── config.py                 # Configuration loading
│
├── tests/                        # Unit tests
├── integration-tests/            # End-to-end tests
├── scripts/                      # Helper scripts
│   ├── publish-budget-alert-event.py
│   ├── test-email-templates.py
│   └── debug-project-discovery.py
│
├── test-data/                    # Sample configurations
│   ├── test-rules.json
│   └── test-rules.yaml
│
├── email-templates/              # Jinja2 email templates
│   ├── budget_alert.html
│   └── policy_action.html
│
├── docs/                         # Documentation
├── tofu/                         # OpenTofu deployment module
├── diagrams/                     # Architecture diagrams
├── Dockerfile                    # Cloud Run container
└── docker-compose.yml            # Local dev environment
```

---

## 🔒 Security

### Best Practices

- ✅ **Never commit** credentials, API keys, or `terraform.tfvars` with sensitive data
- ✅ **Use Secret Manager** for rules configuration and SMTP credentials
- ✅ **Use Workload Identity Federation** for keyless GCP authentication in CI/CD
- ✅ **Follow least privilege** when assigning IAM roles (topic-level, not project-level)
- ✅ **Enable VPC Service Controls** for sensitive projects
- ✅ **Test with dry-run mode** (`DRY_RUN=true`) before production deployment
- ✅ **Review action events** regularly for unexpected policy changes

### Vulnerability Reporting

Please report security vulnerabilities via [GitHub Security Advisories](https://github.com/syalioune/gcp-finops-sentinel/security/advisories).

📖 **Security policy**: [SECURITY.md](SECURITY.md)

---

## 🗺️ Roadmap

- [x] Email notifications via SMTP with HTML templating
- [x] Dynamic project discovery via labels
- [x] Folder-level and organization-level targeting
- [x] Budget and billing account filtering
- [x] Policy action event publishing for auditing
- [x] Cloud Run deployment with container images
- [x] Integration tests with Pub/Sub emulator
- [ ] Multiple organization policies per action
- [ ] Slack/Teams webhook notifications

---

## 💬 Support

| Channel | Purpose |
|---------|---------|
| [GitHub Issues](https://github.com/syalioune/gcp-finops-sentinel/issues) | Bug reports and feature requests |
| [GitHub Discussions](https://github.com/syalioune/gcp-finops-sentinel/discussions) | Questions and community support |
| [Documentation](docs/) | Comprehensive guides and references |

---

## 📝 License

This project is licensed under the **Apache License 2.0** - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

* Built with [Functions Framework](https://github.com/GoogleCloudPlatform/functions-framework-python) for Cloud Run
* Uses [GCP Python Client Libraries](https://github.com/googleapis/google-cloud-python)
* Email templating powered by [Jinja2](https://jinja.palletsprojects.com/)
* Deployed with [OpenTofu](https://opentofu.org/)
* Testing with [pytest](https://pytest.org/) and Docker Compose

> **Note**: This project was developed with AI assistance from [Claude](https://claude.ai) by Anthropic, serving as a development partner throughout design, implementation, testing, and documentation.

---

**Made with ❤️ for cloud cost optimization**

⭐ **Star this repo** if you find it useful!
