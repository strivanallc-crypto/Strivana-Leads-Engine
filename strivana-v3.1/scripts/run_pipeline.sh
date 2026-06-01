#!/bin/bash
# Run Strivana v3.1 pipeline

set -e

echo "🚀 Starting Strivana v3.1 Pipeline..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
    echo "✓ Loaded .env"
else
    echo "⚠ Warning: .env file not found"
fi

# Activate virtual environment if it exists
if [ -d venv ]; then
    source venv/bin/activate
    echo "✓ Activated venv"
fi

# Create logs directory
mkdir -p logs

# Set default values if not provided
export GHL_TOKEN="${GHL_TOKEN:-}"
export LOCATION_ID="${LOCATION_ID:-}"

# Check required environment variables
if [ -z "$GHL_TOKEN" ]; then
    echo "❌ Error: GHL_TOKEN not set"
    exit 1
fi

if [ -z "$LOCATION_ID" ]; then
    echo "❌ Error: LOCATION_ID not set"
    exit 1
fi

# Set targets file
export TARGETS_FILE="${TARGETS_FILE:-config/targets.txt}"

# Run the pipeline
echo "📊 Running pipeline with targets from $TARGETS_FILE..."
python -m src.pipeline.orchestrator

echo "✅ Pipeline complete!"
