# Local Development Guide

Detailed guide for developing and testing locally using Docker Compose, Pub/Sub emulator, and mocked GCP services.

**New to the project?** Start with [CONTRIBUTING.md](CONTRIBUTING.md) for initial setup.

## Prerequisites

- Docker and Docker Compose
- Git Bash or WSL (Windows users)
- Python 3.13+ with pip

## Architecture

The local development environment includes:

```
┌─────────────────────────────────────────────────────────────┐
│                   Local Development Stack                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  Budget Alerts                      Policy Action Events     │
│  Topic (8681)                       Topic (8681)             │
│       │                                    ▲                 │
│       │         ┌────────────────┐         │                 │
│       │         │   Pub/Sub      │         │                 │
│       │         │   Emulator     │         │                 │
│       │         │  (Port 8681)   │         │                 │
│       │         └────────────────┘         │                 │
│       │                                    │                 │
│       ▼                                    │                 │
│  ┌──────────────────────────────────────────────┐           │
│  │   Budget Response Function (Port 8080)       │           │
│  │   - Receives budget alerts via Pub/Sub       │           │
│  │   - Evaluates rules                          │           │
│  │   - DRY_RUN=true (logs actions, no GCP API)  │───────────┘
│  │   - Publishes action events to Pub/Sub       │
│  └──────────────────────────────────────────────┘
│
│  ┌────────────────┐       ┌──────────────────────────┐
│  │ Test Publisher │       │  Integration Tests       │
│  │ Scripts        │       │  - Verify rule logic     │
│  └────────────────┘       │  - Consume action events │
│                            └──────────────────────────┘
│
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

The easiest way to develop and test locally:

```bash
# Start local environment (includes Pub/Sub emulator, MailHog for email testing)
docker compose up -d

# View emails in MailHog web UI
open http://localhost:8025


```bash
# Run all tests (unit + integration)
./scripts/run-tests.sh all

# Unit tests only
./scripts/run-tests.sh unit
# OR: pytest tests/ -v

# Integration tests only
./scripts/run-tests.sh integration

# Coverage report (generates test-results/coverage/index.html)
./scripts/run-tests.sh coverage
```

## Manual Testing

### Start the Local Environment

```bash
docker compose up -d
```

This starts:
- Pub/Sub emulator on `localhost:8681`
- Budget Response Function on `localhost:8080` (with `DRY_RUN=true`)

### View Logs

```bash
# View all logs
docker compose logs -f

# View function logs only
docker compose logs -f budget-function

# View Pub/Sub emulator logs
docker compose logs -f pubsub-emulator
```

### Publish Test Events

```bash
export PUBSUB_EMULATOR_HOST=localhost:8681

# Default test event (90% threshold)
python scripts/publish-budget-alert-event.py

# Predefined scenarios
python scripts/publish-budget-alert-event.py --scenario=critical  # 100%
python scripts/publish-budget-alert-event.py --scenario=high      # 90%
python scripts/publish-budget-alert-event.py --scenario=warning   # 80%

# Custom values
python scripts/publish-budget-alert-event.py \
  --budget=5000 \
  --cost=4500 \
  --billing-account=012345-6789AB-CDEF01 \
  --budget-id=f47ac10b-58cc-4372-a567-0e02b2c3d479
```

### Stop the Environment

```bash
docker compose down
```

## Project Structure

See [README.md](README.md#-development) for project structure overview.

## Configuration

### Environment Variables

The function respects these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `PUBSUB_EMULATOR_HOST` | Pub/Sub emulator address | - |
| `ORGANIZATION_ID` | GCP Organization ID | - |
| `RULES_CONFIG` | Rules as JSON string | - |
| `RULES_CONFIG_PATH` | Path to rules JSON file | `/workspace/rules.json` |
| `DRY_RUN` | Enable dry-run mode (log actions without executing) | `false` |
| `ACTION_EVENT_TOPIC` | Pub/Sub topic for policy action events | - |
| `LOG_LEVEL` | Logging level | `INFO` |

### Test Rules

Test rules are defined in [test-data/test-rules.json](test-data/test-rules.json) and are used for **integration-tests**. Modify this file to test different scenarios.

See [README.md](README.md#-rules-configuration) for complete rule configuration reference.

## Unit Tests

Unit tests are in the `tests/` directory, modularized by component.

Run unit tests:
```bash
# Using Docker
docker compose run --rm test-runner

# Or locally
pytest tests/ -v
```

## Integration Tests

Integration tests in `integration-tests/run_integration_tests.py` verify:

- End-to-end message flow from Pub/Sub to function
- Rule evaluation with real Pub/Sub emulator
- Multiple threshold scenarios
- Project filtering
- Error handling

Run integration tests:
```bash
docker compose --profile integration run --rm integration-test
```

## Debugging

### Enable Debug Logging

Edit `docker-compose.yml` and change:
```yaml
environment:
  - LOG_LEVEL=DEBUG
```

### Attach to Running Container

```bash
docker compose exec budget-function /bin/bash
```

### Run Function Locally (Without Docker)

```bash
cd src

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export PUBSUB_EMULATOR_HOST=localhost:8681
export ORGANIZATION_ID=123456789012
export RULES_CONFIG_PATH=../test-data/test-rules.json
export DRY_RUN=true

# Run with Functions Framework
functions-framework --target=budget_response_handler --debug --port=8080
```

### Interactive Python Testing

```bash
docker compose run --rm budget-function python3

>>> from rule_engine import RuleEngine
>>> from budget_response_engine import BudgetResponseEngine
>>> import json
>>>
>>> # Load test rules
>>> with open('/test-data/test-rules.json') as f:
...     rules_config = json.load(f)
>>>
>>> # Test rule engine
>>> engine = RuleEngine(rules_config)
>>> budget_data = {
...     "costAmount": 950,
...     "budgetAmount": 1000,
...     "labels": {"project_id": "test-project"}
... }
>>> actions = engine.evaluate(budget_data)
>>> print(actions)
```

## Dry-Run Mode

The function supports dry-run mode for testing without making real GCP API calls:

- Set `DRY_RUN=true` environment variable
- Actions are logged but not executed
- Policy action events are still published to Pub/Sub (if configured)
- Useful for integration testing with Pub/Sub emulator

**Example:**
```bash
# In docker-compose.yml
environment:
  - DRY_RUN=true
  - ACTION_EVENT_TOPIC=projects/local-gcp-test-project/topics/policy-action-events
```

Integration tests verify the complete flow by:
1. Publishing budget alerts to Pub/Sub emulator
2. Function processes alerts in dry-run mode (logs actions)
3. Function publishes policy action events to Pub/Sub
4. Tests pull and verify policy action events from Pub/Sub

## Troubleshooting

### Pub/Sub Emulator Not Starting

```bash
# Check if port 8681 is already in use
netstat -an | grep 8681  # Linux/Mac
netstat -an | findstr 8681  # Windows

# Kill existing process or change port in docker-compose.yml
```

### Function Not Receiving Messages

1. Check Pub/Sub topic exists:
```bash
export PUBSUB_EMULATOR_HOST=localhost:8681
gcloud pubsub topics list --project=test-project
```

2. Check function logs:
```bash
docker compose logs -f budget-function
```

3. Verify function is subscribed to topic (Cloud Functions v2 auto-creates subscription)

### Tests Failing

1. Rebuild containers:
```bash
docker compose down
docker compose build --no-cache
docker compose up -d
```

2. Check for Python dependency issues:
```bash
docker compose run --rm budget-function pip list
```

3. Run tests with verbose output:
```bash
docker compose run --rm test-runner pytest -vv -s
```

### Permission Errors (Windows)

If you get permission errors running shell scripts on Git Bash:

```bash
chmod +x scripts/*.sh
./scripts/run-tests.sh
```

## CI/CD Integration

The Docker Compose setup can be used in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    docker compose run --rm test-runner
    docker compose --profile integration run --rm integration-test
```

## Best Practices

1. **Always run unit tests** before integration tests
2. **Use test-data/test-rules.json** for test scenarios
3. **Check logs** when debugging issues
4. **Clean up** with `docker compose down` after testing
5. **Update tests** when adding new features
6. **Use mocks** for GCP API calls in unit tests
7. **Document** new test scenarios

## Additional Resources

- [Cloud Functions Python Docs](https://cloud.google.com/functions/docs/writing)
- [Pub/Sub Emulator Docs](https://cloud.google.com/pubsub/docs/emulator)
- [pytest Documentation](https://docs.pytest.org/)
- [Docker Compose Docs](https://docs.docker.com/compose/)
