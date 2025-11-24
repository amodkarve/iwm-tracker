#!/bin/bash
# Run fuzzy logic optimizer in Docker container

set -e

# Default values
ITERATIONS=${OPTIMIZER_ITERATIONS:-50}
OUTPUT_FILE=${OPTIMIZER_OUTPUT:-""}

echo "Running Fuzzy Logic Optimizer in Docker"
echo "========================================"
echo "Iterations: $ITERATIONS"
if [ -n "$OUTPUT_FILE" ]; then
    echo "Output file: $OUTPUT_FILE"
fi
echo ""

# Build the command
CMD="python scripts/run_optimizer.py"

# Set environment variables
export OPTIMIZER_ITERATIONS=$ITERATIONS
if [ -n "$OUTPUT_FILE" ]; then
    export OPTIMIZER_OUTPUT=$OUTPUT_FILE
fi

# Run in Docker
docker-compose -f docker-compose.test.yml run --rm test $CMD

