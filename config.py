#!/usr/bin/env python3
"""
Project Phoenix: Configuration
"""

import os
from pathlib import Path

# Agnost Configuration
AGNOST_ORG_ID = os.getenv("AGNOST_ORG_ID", "your-org-id")
AGNOST_API_KEY = os.getenv("AGNOST_API_KEY", "your-api-key")

# File Paths
APP_LOG_FILE = Path("/tmp/phoenix_app.log")
APP_STATE_FILE = Path("/tmp/phoenix_app_state.json")
CRASH_TRIGGER_FILE = Path("/tmp/phoenix_crash_trigger")
APP_PROCESS_FILE = Path("/tmp/phoenix_app_pid")

# Monitoring Configuration
MONITOR_CHECK_INTERVAL = 10  # seconds
MONITOR_DURATION = 300  # seconds
MAX_INCIDENTS = 100

# Agent Configuration
MAX_TROUBLESHOOTING_ATTEMPTS = 3
ENABLE_INTENT_DRIFT_CHECK = True

# MCP Server Configuration
MCP_SERVER_HOST = "localhost"
MCP_SERVER_PORT = 8000

# Test Configuration
TEST_SCENARIOS = 50
SCENARIO_ERROR_TYPES = [
    "OOM",
    "PORT_CONFLICT",
    "PERMISSION_ERROR",
    "DISK_FULL"
]

# Dangerous Patterns (Intent Drift Detection)
DANGEROUS_COMMAND_PATTERNS = [
    "rm -rf /",
    "dd if=/dev/zero",
    "mkfs",
    ":() { :|:& };:",  # fork bomb
    "curl | bash",
    "wget | bash",
]

# Dashboard Configuration
DASHBOARD_REFRESH_INTERVAL = 5  # seconds
SHOW_INCIDENT_TRACES = True
SHOW_INTENT_ANALYSIS = True
