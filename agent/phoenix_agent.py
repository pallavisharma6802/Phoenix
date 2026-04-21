#!/usr/bin/env python3
"""
Project Phoenix: Self-Correcting DevOps Agent
Integrated with Agnost SDK for Chain-of-Thought tracking
"""

import os
import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from config import AGNOST_ORG_ID

try:
    import agnost
    from agnost.types import EventData, EventIOData
except ImportError:
    print("Warning: agnost SDK not installed. Run: pip install agnost")
    agnost = None


class IncidentPhase(Enum):
    """Phases of incident resolution"""
    DETECTION = "detection"
    ANALYSIS = "analysis"
    DIAGNOSIS = "diagnosis"
    EXECUTION = "execution"
    VERIFICATION = "verification"
    RESOLVED = "resolved"
    FAILED = "failed"


class IntentType(Enum):
    """Types of agent intent"""
    DIAGNOSE = "diagnose"
    FIX = "fix"
    SAFE_RESTART = "safe_restart"
    ESCALATE = "escalate"
    UNKNOWN = "unknown"


@dataclass
class IncidentReport:
    """Incident tracking record"""
    incident_id: str
    timestamp: str
    error_type: str
    error_message: str
    phase: IncidentPhase
    intent: IntentType
    attempts: int
    logs_analyzed: int
    commands_executed: List[str]
    success: bool
    resolution: Optional[str] = None
    intent_drift_detected: bool = False
    
    def to_dict(self):
        return {
            "incident_id": self.incident_id,
            "timestamp": self.timestamp,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "phase": self.phase.value,
            "intent": self.intent.value,
            "attempts": self.attempts,
            "logs_analyzed": self.logs_analyzed,
            "commands_executed": self.commands_executed,
            "success": self.success,
            "resolution": self.resolution,
            "intent_drift_detected": self.intent_drift_detected,
        }


class PhoenixDevOpsAgent:
    """Self-correcting DevOps agent with Agnost integration"""
    
    def __init__(self, org_id: Optional[str] = None, user_id: str = "phoenix-monitor"):
        self.org_id = org_id or os.getenv("AGNOST_ORG_ID")
        self.user_id = user_id or os.getenv("AGNOST_USER_ID")
        self.logger = logging.getLogger(__name__)
        self.incidents: List[IncidentReport] = []
        self.mcp_tools = {}
        
        if agnost:
            try:
                agnost.init(AGNOST_ORG_ID, endpoint="https://api.agnost.ai")
                agnost.identify(self.user_id, {
                    "userId": self.user_id,
                    "agent": "phoenix-devops-agent",
                    "environment": os.getenv("ENV", "production")
                })
                self.logger.info("Agnost SDK initialized with user identification")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Agnost: {e}")
    
    def log_event(self, event_type: str, message: str, metadata: Dict[str, Any] = None):
        """Log event to both local storage and Agnost"""
        event = {
            "timestamp": datetime.now().isoformat(),
            "type": event_type,
            "message": message,
            "metadata": metadata or {}
        }
        
        self.logger.info(f"[{event_type}] {message}")
        
        # Send to Agnost if available
        if agnost:
            try:
                # This would be part of Agnost session tracking
                pass
            except Exception as e:
                self.logger.warning(f"Failed to log to Agnost: {e}")
    
    def detect_error_type(self, logs: List[Dict]) -> tuple[str, str]:
        """
        Analyze logs to detect error type
        Returns: (error_type, error_message)
        """
        for log in reversed(logs):
            if log.get("type") in ["ERROR", "CRASH"]:
                error_type = log.get("metadata", {}).get("type", "UNKNOWN")
                error_msg = log.get("message", "Unknown error")
                return error_type, error_msg
        
        return "UNKNOWN", "No errors found in logs"
    
    def analyze_logs(self, logs: List[Dict]) -> Dict[str, Any]:
        """
        Analyze error patterns from logs
        """
        error_patterns = {
            "OOM": {
                "pattern": "Memory",
                "cause": "Application out of memory",
                "fix": "Increase available memory or restart app",
                "priority": "high"
            },
            "PORT_CONFLICT": {
                "pattern": "Port",
                "cause": "Another process using app port",
                "fix": "Kill process using port or change port",
                "priority": "medium"
            },
            "PERMISSION_ERROR": {
                "pattern": "Permission",
                "cause": "Insufficient file permissions",
                "fix": "Check file permissions and app user",
                "priority": "medium"
            },
            "DISK_FULL": {
                "pattern": "Disk",
                "cause": "Disk space exhausted",
                "fix": "Free up disk space",
                "priority": "high"
            },
        }
        
        error_type, error_msg = self.detect_error_type(logs)
        
        analysis = {
            "error_type": error_type,
            "error_message": error_msg,
            "pattern_info": error_patterns.get(error_type, {}),
            "crash_count": len([l for l in logs if l.get("type") == "CRASH"]),
            "recent_errors": [l for l in logs[-10:] if l.get("type") in ["ERROR", "CRASH"]]
        }
        
        return analysis
    
    def generate_fix_strategy(self, analysis: Dict[str, Any]) -> str:
        """
        Generate a fix strategy based on error analysis
        Uses Chain-of-Thought to track reasoning
        """
        error_type = analysis.get("error_type", "UNKNOWN")
        
        strategies = {
            "OOM": "Execute: free -h && python3 /path/to/unstable_app.py --restart",
            "PORT_CONFLICT": "Execute: lsof -i :5000 | grep -v PID | awk '{print $2}' | xargs kill -9 && restart_app()",
            "PERMISSION_ERROR": "Execute: chmod -R 755 /path/to/app && chown -R $(whoami) /path/to/app && restart_app()",
            "DISK_FULL": "Execute: du -sh /tmp/* | sort -rh | head -5 && rm -rf /tmp/phoenix_*.bin && restart_app()",
        }
        
        return strategies.get(error_type, "Execute: check_app_status() && restart_app()")

    def validate_command(self, command: str) -> tuple[bool, Optional[str]]:
        """
        Validate command for intent drift
        Returns: (is_safe, reason_if_blocked)
        """
        dangerous_patterns = [
            ("rm -rf /", "Attempting to delete root filesystem"),
            ("dd if=/dev/zero", "Attempting destructive disk operation"),
            ("mkfs", "Attempting to format filesystem"),
            (":() { :|:& };:", "Fork bomb detected"),
            ("curl | bash", "Unsafe script execution"),
        ]
        
        for pattern, reason in dangerous_patterns:
            if pattern in command.lower():
                return False, f"INTENT_DRIFT: {reason}"
        
        return True, None
    
    def execute_fix(self, incident_id: str, command: str, report: IncidentReport) -> bool:
        """
        Execute fix command with intent validation
        """
        is_safe, drift_reason = self.validate_command(command)
        
        if not is_safe:
            report.intent_drift_detected = True
            self.log_event(
                "INTENT_DRIFT_BLOCKED",
                f"Dangerous command blocked: {drift_reason}",
                {"incident_id": incident_id, "command": command}
            )
            return False
        
        self.log_event(
            "EXECUTING_FIX",
            f"Executing fix command",
            {"incident_id": incident_id, "command": command}
        )
        
        report.commands_executed.append(command)
        
        # In a real scenario, this would call the MCP server
        # For now, simulate execution
        time.sleep(1)
        
        return True
    
    def verify_fix(self, incident_id: str) -> bool:
        """
        Verify that the fix was successful
        """
        self.log_event(
            "VERIFYING_FIX",
            "Checking app status after fix",
            {"incident_id": incident_id}
        )
        
        # Simulate verification check
        time.sleep(1)
        
        return True
    
    def run_troubleshooting_loop(self, logs: List[Dict], max_attempts: int = 3) -> IncidentReport:
        """
        Main troubleshooting loop - THE CORE OF PHOENIX
        This is where Chain-of-Thought tracking happens
        """
        incident_id = f"incident_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        report = IncidentReport(
            incident_id=incident_id,
            timestamp=datetime.now().isoformat(),
            error_type="PENDING",
            error_message="",
            phase=IncidentPhase.DETECTION,
            intent=IntentType.DIAGNOSE,
            attempts=0,
            logs_analyzed=len(logs),
            commands_executed=[],
            success=False
        )
        
        self.log_event("INCIDENT_START", f"Starting troubleshooting loop", {"incident_id": incident_id})
        
        if agnost:
            try:
                agnost.track(
                    "troubleshooting_start",
                    input=EventIOData(data={
                        "logs_count": len(logs),
                        "incident_id": incident_id,
                        "user_id": self.user_id,
                        "session_id": incident_id,
                        "org_id": self.org_id
                    }),
                    metadata={
                        "agent": "phoenix-devops-agent",
                        "tool": "phoenix-troubleshooting-loop"
                    }
                )
            except Exception as e:
                self.logger.debug(f"Agnost tracking failed (non-critical): {e}")
        
        # ========== PHASE 1: DETECTION & ANALYSIS ==========
        report.phase = IncidentPhase.ANALYSIS
        report.intent = IntentType.DIAGNOSE
        
        analysis = self.analyze_logs(logs)
        report.error_type = analysis.get("error_type")
        report.error_message = analysis.get("error_message")
        
        self.log_event(
            "ERROR_DETECTED",
            f"Error type: {report.error_type}",
            {"analysis": analysis}
        )
        
        report.phase = IncidentPhase.DIAGNOSIS
        report.intent = IntentType.FIX
        
        fix_strategy = self.generate_fix_strategy(analysis)
        
        self.log_event(
            "FIX_STRATEGY_GENERATED",
            f"Strategy: {fix_strategy}",
            {"incident_id": incident_id}
        )
        
        report.phase = IncidentPhase.EXECUTION
        
        for attempt in range(1, max_attempts + 1):
            report.attempts = attempt
            
            self.log_event(
                "FIX_ATTEMPT",
                f"Attempt {attempt}/{max_attempts}",
                {"incident_id": incident_id, "strategy": fix_strategy}
            )
            
            # Validate command before execution
            success = self.execute_fix(incident_id, fix_strategy, report)
            
            if not success:
                if report.intent_drift_detected:
                    report.phase = IncidentPhase.FAILED
                    report.resolution = "Intent drift detected, aborting execution"
                    self.log_event("INCIDENT_FAILED", "Intent drift prevented fix execution")
                    
                    if agnost:
                        try:
                            agnost.track(
                                "troubleshooting_end",
                                input=EventIOData(data={"incident_id": incident_id}),
                                output=EventIOData(data={
                                    "success": False,
                                    "reason": "intent_drift_detected",
                                    "error_type": report.error_type
                                }),
                                metadata={
                                    "user_id": self.user_id,
                                    "session_id": incident_id,
                                    "agent": "phoenix-devops-agent"
                                }
                            )
                        except Exception as e:
                            self.logger.debug(f"Agnost tracking failed (non-critical): {e}")
                    
                    self.incidents.append(report)
                    return report
                continue
            
            report.phase = IncidentPhase.VERIFICATION
            
            is_fixed = self.verify_fix(incident_id)
            
            if is_fixed:
                report.phase = IncidentPhase.RESOLVED
                report.success = True
                report.resolution = f"Fixed on attempt {attempt}"
                
                self.log_event(
                    "INCIDENT_RESOLVED",
                    f"Incident resolved after {attempt} attempt(s)",
                    {"incident_id": incident_id}
                )
                
                if agnost:
                    try:
                        agnost.track(
                            "troubleshooting_end",
                            input=EventIOData(data={"incident_id": incident_id}),
                            output=EventIOData(data={
                                "success": True,
                                "resolution": report.resolution,
                                "error_type": report.error_type,
                                "attempts": attempt
                            }),
                            metadata={
                                "user_id": self.user_id,
                                "session_id": incident_id,
                                "agent": "phoenix-devops-agent"
                            }
                        )
                    except Exception as e:
                        self.logger.debug(f"Agnost tracking failed (non-critical): {e}")
                
                self.incidents.append(report)
                return report
            else:
                self.log_event(
                    "FIX_FAILED",
                    f"Attempt {attempt} unsuccessful, trying again...",
                    {"incident_id": incident_id}
                )
        
        # Max attempts exceeded
        report.phase = IncidentPhase.FAILED
        report.success = False
        report.resolution = f"Failed after {max_attempts} attempts"
        
        self.log_event(
            "INCIDENT_FAILED",
            f"Could not resolve incident after {max_attempts} attempts",
            {"incident_id": incident_id}
        )
        
        if agnost:
            try:
                agnost.track(
                    "troubleshooting_end",
                    input=EventIOData(data={"incident_id": incident_id}),
                    output=EventIOData(data={
                        "success": False,
                        "reason": "max_attempts_exceeded",
                        "error_type": report.error_type,
                        "attempts": max_attempts
                    }),
                    metadata={
                        "user_id": self.user_id,
                        "session_id": incident_id,
                        "agent": "phoenix-devops-agent"
                    }
                )
            except Exception as e:
                self.logger.debug(f"Agnost tracking failed (non-critical): {e}")
        
        self.incidents.append(report)
        return report
    
    def get_incident_summary(self) -> Dict[str, Any]:
        """Generate summary of all incidents for dashboard"""
        total_incidents = len(self.incidents)
        resolved = len([i for i in self.incidents if i.success])
        
        error_breakdown = {}
        for incident in self.incidents:
            error_type = incident.error_type
            error_breakdown[error_type] = error_breakdown.get(error_type, 0) + 1
        
        intent_drift_count = len([i for i in self.incidents if i.intent_drift_detected])
        
        return {
            "total_incidents": total_incidents,
            "resolved": resolved,
            "resolution_rate": f"{(resolved / total_incidents * 100):.1f}%" if total_incidents > 0 else "0%",
            "error_breakdown": error_breakdown,
            "intent_drift_detections": intent_drift_count,
            "incidents": [i.to_dict() for i in self.incidents[-10:]]  # Last 10
        }


def generate_review_report(agent: PhoenixDevOpsAgent, output_file: str = "/tmp/phoenix_review.json"):
    """Generate review-ready report for founders"""
    summary = agent.get_incident_summary()
    
    report = {
        "title": "Project Phoenix: DevOps Agent Review",
        "generated_at": datetime.now().isoformat(),
        "summary": summary,
        "findings": {
            "agent_reliability": f"{summary['resolution_rate']} of incidents auto-resolved",
            "intent_drift_protection": f"{summary['intent_drift_detections']} dangerous commands blocked",
            "error_diversity": f"Handled {len(summary['error_breakdown'])} error types",
            "cost_efficiency": "Will be measured based on token usage in Agnost dashboard"
        },
        "recommendations": [
            "Intent drift detection prevented catastrophic errors",
            "Consider increasing max_attempts for complex errors",
            "Monitor token usage in Agnost dashboard for cost optimization"
        ]
    }
    
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)
    
    return report


if __name__ == "__main__":
    # Test the agent
    agent = PhoenixDevOpsAgent(user_id="phoenix-demo")
    
    # Simulate logs for testing
    test_logs = [
        {
            "timestamp": "2026-04-21T10:00:00",
            "type": "APP_START",
            "message": "Application started",
            "metadata": {}
        },
        {
            "timestamp": "2026-04-21T10:01:00",
            "type": "ERROR",
            "message": "Application crashed: Cannot allocate memory",
            "metadata": {"type": "OOM"}
        }
    ]
    
    # Run troubleshooting loop
    report = agent.run_troubleshooting_loop(test_logs)
    
    # Generate review report
    review = generate_review_report(agent)
    
    print("\n" + "="*60)
    print("INCIDENT REPORT")
    print("="*60)
    print(json.dumps(report.to_dict(), indent=2))
    
    print("\n" + "="*60)
    print("REVIEW REPORT")
    print("="*60)
    print(json.dumps(review, indent=2))
