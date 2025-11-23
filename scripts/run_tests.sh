#!/bin/bash
# Test runner script for IWM Tracker
# Runs tests inside Docker container using docker-compose
# Usage: ./scripts/run_tests.sh [pytest-args]
#        ./scripts/run_tests.sh --build [pytest-args]  # Rebuild image first

set -e  # Exit on error

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

echo "🧪 Running IWM Tracker Tests in Docker"
echo "======================================"
echo ""

# Build the test image if --build flag is passed
if [ "$1" = "--build" ]; then
    echo "📦 Building test Docker image..."
    docker-compose -f docker-compose.test.yml build
    echo "✅ Test image built"
    echo ""
    shift
fi

# Run tests with any additional pytest arguments
echo "🚀 Running tests..."
echo ""

# Use docker-compose to run tests
# If arguments are provided, pass them to pytest, otherwise use default
if [ $# -eq 0 ]; then
    docker-compose -f docker-compose.test.yml run --rm test pytest -v
else
    docker-compose -f docker-compose.test.yml run --rm test pytest "$@"
fi

echo ""
echo "✅ Tests completed"

