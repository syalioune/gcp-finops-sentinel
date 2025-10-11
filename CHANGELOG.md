# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-01-23

### Added
- Initial release of GCP FinOps Sentinel
- Cloud Run deployment with Eventarc triggers for budget alerts
- Budget threshold-based policy enforcement with flexible rule engine
- Rule engine with flexible threshold operators (`>=`, `>`, `==`, `<`, `<=`, `min`, `max`)
- Support for range-based threshold conditions using operator arrays
- Multi-target support: projects, folders, organizations, and label-based discovery
- Organization policy enforcement (service restrictions, custom constraints)
- Dynamic project discovery via Resource Manager API label queries
- Email notifications via SMTP with professional Jinja2 templates
  - Mobile-responsive HTML templates with severity-based color coding
  - Budget alert and policy action notification templates
  - Customizable email templates with full Jinja2 support
- Policy action event publishing to Pub/Sub for observability and auditing
- Dry-run mode for testing rules without applying policies
- Comprehensive unit and integration test suite (82+ tests)
- Docker Compose local development environment
  - Pub/Sub emulator for budget alert testing
  - MailHog for email template testing and development
- Production-ready OpenTofu/Terraform deployment module
  - Complete Cloud Run service with Eventarc integration
  - Secret Manager integration for rules and SMTP credentials
  - IAM service accounts with least-privilege permissions
  - Uptime monitoring and alerting
- Complete documentation
  - Comprehensive README with quick start guide
  - CLAUDE.md for AI-assisted development
  - OpenTofu deployment guide
  - IAM permissions reference
  - Local development guide
  - Contributing guidelines
- Pre-commit hooks for code quality
  - Conventional Commits enforcement
  - Black and isort for Python formatting
  - Pylint with minimum score 8.0
  - Dockerfile linting with hadolint
  - Secret detection with detect-secrets
- GitHub Actions CI/CD workflows
  - Unit and integration testing
  - Security scanning with Trivy
  - Multi-registry Docker image publishing (Artifact Registry + Docker Hub)
  - Automated releases on version tags
- Helper scripts
  - Budget alert event publisher for testing
  - Policy action event consumer
  - Email template testing utility
  - Project discovery debugger

### Security
- No hardcoded secrets or credentials
- Secret Manager integration for sensitive configuration
- Least-privilege IAM roles and service accounts
- TLS support for SMTP connections
- Comprehensive secret detection in pre-commit hooks

[1.0.0]: https://github.com/syalioune/gcp-finops-sentinel/releases/tag/v1.0.0
