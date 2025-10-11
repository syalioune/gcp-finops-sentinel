#!/bin/bash
# Script to run tests for Budget Response Function

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo "Budget Response Function - Test Runner"
echo "========================================"
echo ""

# Function to display usage
usage() {
    echo "Usage: $0 [unit|integration|all|coverage]"
    echo ""
    echo "Options:"
    echo "  unit         - Run unit tests only"
    echo "  integration  - Run integration tests only"
    echo "  all          - Run all tests"
    echo "  coverage     - Run tests with coverage report"
    echo ""
    exit 1
}

# Change to project root
cd "$PROJECT_ROOT"

# Parse arguments
TEST_TYPE="${1:-all}"

case "$TEST_TYPE" in
    unit)
        echo "Running unit tests..."
        docker compose run --rm --build test-runner
        ;;

    integration)
        echo "Starting services..."
        docker compose up --build -d pubsub-emulator budget-function

        echo "Waiting for services to be ready..."
        sleep 5

        echo "Running integration tests..."
        docker compose --profile integration run --rm integration-test

        echo "Stopping services..."
        docker compose down -v
        ;;

    coverage)
        echo "Running tests with coverage..."
        docker compose --profile test run --rm test-runner

        echo ""
        echo "Coverage report generated in test-results/coverage/"
        ;;

    all)
        echo "Running unit tests..."
        docker compose run --rm --build test-runner

        echo ""
        echo "Starting services for integration tests..."
        docker compose up -d --build pubsub-emulator budget-function

        echo "Waiting for services to be ready..."
        sleep 10

        echo ""
        echo "Running integration tests..."
        docker compose --profile integration run --rm --build integration-test

        echo ""
        echo "Stopping services..."
        docker compose down -v
        ;;

    *)
        echo "Error: Unknown test type '$TEST_TYPE'"
        echo ""
        usage
        ;;
esac

echo ""
echo "========================================"
echo "Tests completed!"
echo "========================================"
