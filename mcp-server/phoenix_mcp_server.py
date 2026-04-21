#!/usr/bin/env python3
"""
Project Phoenix: MCP Server
Provides DevOps tools: shell commands, log analysis, app restart, diagnostics.
"""

import json
import os
import signal
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from agnost_mcp import config, track


load_dotenv(Path(__file__).resolve().parent.parent / ".env")


server = FastMCP("phoenix-devops-server")

APP_LOG = Path("/tmp/phoenix_app.log")
APP_STATE = Path("/tmp/phoenix_app_state.json")
APP_PROCESS_FILE = Path("/tmp/phoenix_app_pid")


@server.tool()
def execute_shell(command: str) -> Dict[str, Any]:
    """Execute a shell command with safety validation."""
    dangerous_patterns = [
        "rm -rf /",
        "dd if=/dev/zero",
        "mkfs",
        ":() { :|:& };:",
        "curl | bash",
        "wget | bash",
    ]

    command_lower = command.lower()
    for pattern in dangerous_patterns:
        if pattern in command_lower:
            return {
                "error": "INTENT_DRIFT_DETECTED",
                "message": f"Dangerous command blocked: '{pattern}' detected",
                "status": "BLOCKED",
                "command": command,
                "success": False,
            }

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {
            "status": "success" if result.returncode == 0 else "error",
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
            "command": command,
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "error",
            "message": "Command timeout (30s exceeded)",
            "command": command,
            "success": False,
        }
    except Exception as exc:
        return {
            "status": "error",
            "message": str(exc),
            "command": command,
            "success": False,
        }


@server.tool()
def get_app_logs(lines: int = 50, error_only: bool = False) -> Dict[str, Any]:
    """Retrieve application logs for diagnostics."""
    if not APP_LOG.exists():
        return {
            "status": "error",
            "message": "No log file found",
            "path": str(APP_LOG),
            "success": False,
        }

    try:
        with open(APP_LOG, "r", encoding="utf-8") as handle:
            all_logs = [json.loads(line) for line in handle.readlines()]

        if error_only:
            all_logs = [log for log in all_logs if log.get("type") in ["ERROR", "CRASH"]]

        recent_logs = all_logs[-lines:]
        return {
            "status": "success",
            "total_logs": len(all_logs),
            "returned_logs": len(recent_logs),
            "logs": recent_logs,
            "success": True,
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc), "success": False}


@server.tool()
def check_app_status() -> Dict[str, Any]:
    """Check if app is running and retrieve state."""
    try:
        state: Dict[str, Any] = {}
        if APP_STATE.exists():
            with open(APP_STATE, "r", encoding="utf-8") as handle:
                state = json.load(handle)

        is_running = False
        if APP_PROCESS_FILE.exists():
            with open(APP_PROCESS_FILE, "r", encoding="utf-8") as handle:
                pid = int(handle.read().strip())
            try:
                os.kill(pid, 0)
                is_running = True
            except OSError:
                is_running = False

        return {
            "status": "success",
            "app_running": is_running,
            "state": state,
            "timestamp": datetime.now().isoformat(),
            "success": True,
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc), "success": False}


@server.tool()
def restart_app(force: bool = False) -> Dict[str, Any]:
    """Restart the Phoenix application."""
    try:
        if APP_PROCESS_FILE.exists():
            with open(APP_PROCESS_FILE, "r", encoding="utf-8") as handle:
                pid = int(handle.read().strip())
            try:
                os.kill(pid, signal.SIGKILL if force else signal.SIGTERM)
                time.sleep(1)
            except ProcessLookupError:
                pass

        app_script = Path(__file__).resolve().parent.parent / "app" / "unstable_app.py"
        proc = subprocess.Popen(
            ["python3", str(app_script), "60"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        with open(APP_PROCESS_FILE, "w", encoding="utf-8") as handle:
            handle.write(str(proc.pid))

        return {
            "status": "success",
            "message": "Application restarted",
            "new_pid": proc.pid,
            "method": "SIGKILL" if force else "SIGTERM",
            "success": True,
        }
    except Exception as exc:
        return {"status": "error", "message": str(exc), "success": False}


@server.tool()
def analyze_errors() -> Dict[str, Any]:
    """Analyze error patterns from logs to suggest fixes."""
    if not APP_LOG.exists():
        return {"status": "error", "message": "No logs to analyze", "success": False}

    try:
        with open(APP_LOG, "r", encoding="utf-8") as handle:
            logs = [json.loads(line) for line in handle.readlines()]

        error_types: Dict[str, int] = {}
        for log in logs:
            if log.get("type") in ["ERROR", "CRASH"]:
                error_type = log.get("metadata", {}).get("type", "UNKNOWN")
                error_types[error_type] = error_types.get(error_type, 0) + 1

        suggestions = {
            "OOM": "Increase memory allocation or optimize memory usage",
            "PORT_CONFLICT": "Kill process using port 5000 or change app port",
            "PERMISSION_ERROR": "Check file permissions and app user permissions",
            "DISK_FULL": "Clear disk space or reduce data retention",
        }

        analysis = {
            "total_errors": len([log for log in logs if log.get("type") in ["ERROR", "CRASH"]]),
            "error_breakdown": error_types,
            "suggested_fixes": {k: suggestions.get(k, "Unknown error type") for k in error_types.keys()},
            "most_common_error": max(error_types.items(), key=lambda item: item[1])[0] if error_types else None,
        }

        return {"status": "success", "analysis": analysis, "success": True}
    except Exception as exc:
        return {"status": "error", "message": str(exc), "success": False}


track(
    server,
    os.getenv("AGNOST_ORG_ID", "6a08ee1e-6f58-46db-b7c6-329d77957b01"),
    config(
        endpoint="https://api.agnost.ai",
        identify=lambda req, env: {
            "userId": ((req or {}).get("headers", {}).get("x-user-id"))
            or env.get("USER_ID")
            or env.get("USER")
            or "phoenix-monitor",
            "email": ((req or {}).get("headers", {}).get("x-user-email"))
            or env.get("USER_EMAIL"),
            "sessionId": ((req or {}).get("headers", {}).get("x-session-id"))
            or ((req or {}).get("headers", {}).get("x-conversation-id"))
            or env.get("SESSION_ID"),
        },
    ),
)


if __name__ == "__main__":
    server.run()
