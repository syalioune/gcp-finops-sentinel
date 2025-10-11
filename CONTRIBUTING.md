# Contributing to GCP FinOps Sentinel

Thank you for considering contributing to GCP FinOps Sentinel! This document provides guidelines for contributing to the project.

## Code of Conduct

This project adheres to a [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues. When creating a bug report, include as many details as possible:

- **Use a clear and descriptive title**
- **Describe the exact steps to reproduce the problem**
- **Provide specific examples**
- **Describe the behavior you observed and what you expected**
- **Include logs, screenshots, or error messages**
- **Specify your environment** (Python version, GCP region, etc.)

### Suggesting Enhancements

Enhancement suggestions are welcome! Please:

- **Use a clear and descriptive title**
- **Provide a step-by-step description of the suggested enhancement**
- **Explain why this enhancement would be useful**
- **List any alternatives you've considered**

### Pull Requests

1. **Fork the repository** and create your branch from `main`
2. **Make your changes** following the code style guidelines
3. **Add tests** for new functionality
4. **Ensure all tests pass** locally
5. **Update documentation** as needed
6. **Commit with meaningful messages** using [Conventional Commits](https://www.conventionalcommits.org/)
7. **Push to your fork** and submit a pull request

## Development Setup

### Prerequisites

- Python 3.13+ (3.12+ supported)
- Docker and Docker Compose
- Git
- A GCP project for testing (optional, for integration tests)

### Quick Start (5 minutes)

```bash
# 1. Clone your fork
git clone https://github.com/YOUR_USERNAME/gcp-finops-sentinel.git
cd gcp-finops-sentinel

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r src/requirements.txt
pip install -r src/requirements-test.txt

# 4. Install pre-commit hooks (IMPORTANT!)
pre-commit install
pre-commit install --hook-type commit-msg

# 5. Verify setup
pytest tests/ -v

# 6. Start coding!
git checkout -b feat/my-feature
```

### Local Development Environment

```bash
# Start Docker Compose environment (Pub/Sub emulator + function)
docker compose up -d

# View logs
docker compose logs -f budget-function

# Publish test event
PUBSUB_EMULATOR_HOST=localhost:8681 python scripts/publish-budget-alert-event.py --scenario=high

# Stop environment
docker compose down
```

**For detailed Docker workflows and debugging**: See [LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md)

## Code Style & Quality

### Pre-commit Hooks (Automated Quality Checks)

All code quality checks run automatically on every commit via [pre-commit](https://pre-commit.com/). No manual formatting needed!

**What gets checked:**

1. **Commit Messages** - [Conventional Commits](https://www.conventionalcommits.org/) format (enforced)
2. **Code Formatting** - Black (line length: 100)
3. **Import Sorting** - isort (compatible with Black)
4. **Code Linting** - Pylint (minimum score: 8.0/10)
5. **File Validation** - YAML, JSON, trailing whitespace, end-of-file
6. **Dockerfile Linting** - hadolint
7. **Secret Detection** - detect-secrets

**Manual run (when needed):**

```bash
# Run all checks on all files
pre-commit run --all-files

# Run specific check
pre-commit run black --all-files
pre-commit run pylint --all-files

# Skip hooks (emergency only, not recommended)
git commit --no-verify -m "emergency fix"
```

### Commit Message Format (Enforced)

Format: `<type>(<scope>): <description>`

**Valid types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting changes
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `build`: Build system changes
- `ci`: CI configuration changes
- `chore`: Maintenance tasks
- `revert`: Revert previous commit

**Examples:**
```bash
feat(rules): add budget ID filtering with UUID support
fix(handler): extract attributes from Pub/Sub message
docs(readme): update filtering documentation
test(integration): add billing account filter tests
refactor(engine): split main.py into separate modules
```

**Common issues:**
```bash
# ❌ Bad (missing type)
git commit -m "add new feature"

# ❌ Bad (uppercase description)
git commit -m "feat: Add new feature"

# ❌ Bad (ends with period)
git commit -m "feat: add new feature."

# ✅ Good
git commit -m "feat: add new feature"
```

### Troubleshooting Pre-commit Hooks

**Pylint failing (score < 8.0)?**
```bash
# Check your score
pylint src/ tests/ --score=yes

# Fix issues or adjust configuration if reasonable
```

**Black/isort modified files?**
1. Changes are automatically staged
2. Review: `git diff --cached`
3. Commit again: `git commit`

**False positive secret detected?**
```bash
# Add to baseline
detect-secrets scan --baseline .secrets.baseline
```

## Testing

### Running Tests

```bash
# Quick test (unit tests only)
pytest tests/ -v

# All tests (unit + integration)
./scripts/run-tests.sh all

# Integration tests with Docker Compose
./scripts/run-tests.sh integration

# With coverage
pytest tests/ -v --cov=src --cov-report=html
```

### Testing Guidelines

- ✅ Write tests for all new features
- ✅ Update tests when modifying existing code
- ✅ Use descriptive test names
- ✅ Mock external dependencies (GCP APIs)
- ✅ Test edge cases and error conditions
- ✅ Maintain test coverage above 80%

**For detailed testing workflows**: See [LOCAL_DEVELOPMENT.md](docs/LOCAL_DEVELOPMENT.md)

## Documentation

### Code Documentation

- Docstrings for all classes and functions
- Google-style docstrings preferred
- Include parameter types and return values
- Explain complex logic with comments

Example:

```python
def apply_constraint(
    self,
    project_id: str,
    constraint: str,
    enforce: bool = True
) -> bool:
    """
    Apply an organization policy constraint.

    Args:
        project_id: GCP Project ID
        constraint: Constraint name (e.g., 'compute.vmExternalIpAccess')
        enforce: Whether to enforce the constraint

    Returns:
        bool: True if successful, False otherwise
    """
    # Implementation
```

### README Updates

Update README.md when:
- Adding new features
- Changing configuration
- Updating prerequisites
- Adding new dependencies

## Pull Request Process

1. **Update the README** with details of changes if applicable
2. **Update the documentation** in relevant .md files
3. **Add tests** that prove your fix or feature works
4. **Ensure CI passes** - all tests, linting, and security scans must pass
5. **Request review** from maintainers
6. **Address feedback** promptly
7. **Squash commits** if requested before merging

### PR Checklist

- [ ] Code follows project style guidelines
- [ ] Self-review of code completed
- [ ] Comments added for complex code
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] All tests pass locally
- [ ] No new warnings introduced
- [ ] Commit messages follow Conventional Commits

## Workload Identity Federation Setup

For contributors needing to test CI/CD:

### 1. Create Workload Identity Pool

```bash
gcloud iam workload-identity-pools create github-pool \
  --project=PROJECT_ID \
  --location=global \
  --display-name="GitHub Actions Pool"
```

### 2. Add GitHub Provider

```bash
gcloud iam workload-identity-pools providers create-oidc github-provider \
  --project=PROJECT_ID \
  --location=global \
  --workload-identity-pool=github-pool \
  --display-name="GitHub Provider" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository" \
  --issuer-uri="https://token.actions.githubusercontent.com"
```

### 3. Create Service Account

```bash
gcloud iam service-accounts create github-actions \
  --project=PROJECT_ID \
  --display-name="GitHub Actions"
```

### 4. Grant Permissions

```bash
# Artifact Registry Writer
gcloud artifacts repositories add-iam-policy-binding REPO_NAME \
  --project=PROJECT_ID \
  --location=REGION \
  --member="serviceAccount:github-actions@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"
```

### 5. Bind Service Account

```bash
gcloud iam service-accounts add-iam-policy-binding \
  github-actions@PROJECT_ID.iam.gserviceaccount.com \
  --project=PROJECT_ID \
  --role="roles/iam.workloadIdentityUser" \
  --member="principalSet://iam.googleapis.com/projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/attribute.repository/YOUR_ORG/gcp-finops-sentinel"
```

### 6. Configure GitHub Secrets

After setting up Workload Identity Federation, configure these secrets in your repository:

**Settings → Secrets and variables → Actions → Repository secrets:**

1. `WIF_PROVIDER`: Workload Identity Provider (from step 2)
   ```
   projects/PROJECT_NUMBER/locations/global/workloadIdentityPools/github-pool/providers/github-provider
   ```

2. `WIF_SERVICE_ACCOUNT`: Service account email (from step 3)
   ```
   github-actions@PROJECT_ID.iam.gserviceaccount.com
   ```

3. `ARTIFACT_REGISTRY_URL`: Container registry URL
   ```
   REGION-docker.pkg.dev/PROJECT_ID/REPO_NAME
   ```

4. `GCP_PROJECT_ID`: Your GCP project ID

5. `GCP_REGION`: Deployment region (e.g., `us-central1`)

6. `DOCKERHUB_USERNAME`: Docker Hub username (for multi-registry push)

7. `DOCKERHUB_TOKEN`: Docker Hub access token (generate from Docker Hub settings)


## Release Process

Maintainers handle releases:

1. Update version in relevant files
2. Update CHANGELOG.md
3. Create a git tag with semantic version
4. Push tag to trigger release workflow
5. GitHub Actions builds and publishes Docker image
6. GitHub Release is created automatically

Version format: `vMAJOR.MINOR.PATCH` (e.g., `v1.2.3`)

## Questions?

- Open a [GitHub Discussion](https://github.com/YOUR_ORG/gcp-finops-sentinel/discussions)
- Check existing [Issues](https://github.com/YOUR_ORG/gcp-finops-sentinel/issues)
- Review [Documentation](README.md)

## License

By contributing, you agree that your contributions will be licensed under the Apache License 2.0.
