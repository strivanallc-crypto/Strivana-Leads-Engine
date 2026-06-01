#!/bin/bash
# Stop token bleed by pausing old Strivana jobs

echo "🛑 Stopping token bleed..."

hermes pause strivana-autonomous-v3
hermes pause strivana-collect
hermes pause strivana-score
hermes pause strivana-push
hermes pause gateway-watchdog-agent

echo "✅ Token bleed stopped. Enable v3.1 jobs manually."
echo ""
echo "To enable v3.1 pipeline:"
echo "  hermes enable strivana-v3.1-pipeline"
echo "  hermes enable strivana-v3.1-healthcheck"
