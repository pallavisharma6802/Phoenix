#!/usr/bin/env python3
"""
Project Phoenix: Main Entry Point
Orchestrates the monitoring, error detection, and self-correction loop
"""

import os
import sys
import json
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

# Add agent to path
sys.path.insert(0, str(Path(__file__).parent))

from agent.phoenix_agent import PhoenixDevOpsAgent, generate_review_report
from tests.test_scenarios import TestScenarioRunner


def setup_logging(log_file: str = "/tmp/phoenix_monitor.log"):
    """Configure logging"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


class PhoenixMonitor:
    """Continuous monitoring and self-correction service"""
    
    def __init__(self, check_interval: int = 10, max_incidents: int = 100):
        self.logger = setup_logging()
        self.check_interval = check_interval
        self.max_incidents = max_incidents
        self.agent = PhoenixDevOpsAgent()
        self.app_log_file = Path("/tmp/phoenix_app.log")
        self.last_log_position = 0
    
    def read_new_logs(self) -> list:
        """Read only new log entries since last check"""
        if not self.app_log_file.exists():
            return []
        
        try:
            with open(self.app_log_file, "r") as f:
                lines = f.readlines()
            
            new_logs = []
            for line in lines[self.last_log_position:]:
                try:
                    log_entry = json.loads(line.strip())
                    new_logs.append(log_entry)
                except json.JSONDecodeError:
                    pass
            
            self.last_log_position = len(lines)
            return new_logs
        
        except Exception as e:
            self.logger.error(f"Error reading logs: {e}")
            return []
    
    def check_for_errors(self, logs: list) -> bool:
        """Check if any errors in logs"""
        for log in logs:
            if log.get("type") in ["ERROR", "CRASH"]:
                return True
        return False
    
    def monitor_loop(self, duration: int = 300):
        """
        Main monitoring loop
        
        Args:
            duration: How long to run (seconds)
        """
        self.logger.info(f"Starting Phoenix monitor (running for {duration}s)")
        print(f"\n{'='*70}")
        print("PROJECT PHOENIX: MONITORING LOOP")
        print(f"{'='*70}")
        print(f"Monitor interval: {self.check_interval}s")
        print(f"Duration: {duration}s\n")
        
        start_time = time.time()
        check_count = 0
        
        try:
            while time.time() - start_time < duration:
                check_count += 1
                
                # Read new logs
                new_logs = self.read_new_logs()
                
                if new_logs:
                    self.logger.info(f"Check #{check_count}: Read {len(new_logs)} log entries")
                    
                    # Check for errors
                    if self.check_for_errors(new_logs):
                        self.logger.warning("Errors detected! Initiating troubleshooting loop...")
                        
                        # Run agent's troubleshooting loop
                        report = self.agent.run_troubleshooting_loop(new_logs)
                        
                        self.logger.info(f"Troubleshooting complete: {report.resolution}")
                
                time.sleep(self.check_interval)
            
            self.logger.info(f"Monitor stopped after {check_count} checks")
        
        except KeyboardInterrupt:
            self.logger.info("Monitor interrupted by user")
        
        # Generate final report
        return self.agent.get_incident_summary()


def main():
    parser = argparse.ArgumentParser(description="Project Phoenix DevOps Agent")
    
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Start monitoring service")
    monitor_parser.add_argument("--duration", type=int, default=300, help="Duration in seconds")
    monitor_parser.add_argument("--interval", type=int, default=10, help="Check interval in seconds")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Run test scenarios")
    test_parser.add_argument("--scenarios", type=int, default=50, help="Number of test scenarios")
    
    # Demo command
    demo_parser = subparsers.add_parser("demo", help="Run interactive demo")
    
    args = parser.parse_args()
    
    if args.command == "monitor":
        monitor = PhoenixMonitor(check_interval=args.interval)
        summary = monitor.monitor_loop(duration=args.duration)
        
        print("\n" + "="*70)
        print("MONITORING COMPLETE")
        print("="*70)
        print(json.dumps(summary, indent=2))
    
    elif args.command == "test":
        runner = TestScenarioRunner(num_iterations=args.scenarios)
        metrics = runner.run_all_scenarios()
        report = runner.generate_report()
        runner.print_summary()
        
        print(f"\nReport saved to: /tmp/phoenix_test_report.json")
    
    elif args.command == "demo":
        demo()
    
    else:
        parser.print_help()


def demo():
    """Interactive demo of Phoenix agent"""
    logger = setup_logging()
    logger.info("Starting Phoenix interactive demo...")
    
    print("\n" + "="*70)
    print("PROJECT PHOENIX: INTERACTIVE DEMO")
    print("="*70 + "\n")
    
    agent = PhoenixDevOpsAgent(user_id="demo-user")
    
    # Create demo error logs
    demo_logs = [
        {"timestamp": time.time(), "type": "APP_START", "message": "Application started", "metadata": {}},
        {"timestamp": time.time() + 5, "type": "APP_HEALTHY", "message": "App running", "metadata": {}},
        {
            "timestamp": time.time() + 15,
            "type": "ERROR",
            "message": "Cannot allocate memory",
            "metadata": {"type": "OOM"}
        },
        {
            "timestamp": time.time() + 17,
            "type": "CRASH",
            "message": "Application crashed: Out of memory",
            "metadata": {"type": "OOM", "total_crashes": 1}
        }
    ]
    
    print("Simulating application crash from OOM error...\n")
    
    report = agent.run_troubleshooting_loop(demo_logs, max_attempts=3)
    
    print("\n" + "="*70)
    print("INCIDENT REPORT")
    print("="*70)
    print(json.dumps(report.to_dict(), indent=2))
    
    print("\n" + "="*70)
    print("AGENT ANALYSIS")
    print("="*70)
    print(f"Error Type: {report.error_type}")
    print(f"Error Message: {report.error_message}")
    print(f"Phase: {report.phase.value}")
    print(f"Attempts: {report.attempts}")
    print(f"Resolved: {report.success}")
    print(f"Resolution: {report.resolution}")
    print(f"Intent Drift Detected: {report.intent_drift_detected}")
    print(f"Commands Executed: {len(report.commands_executed)}")
    
    # Generate review report
    print("\n" + "="*70)
    print("GENERATING FOUNDER REVIEW REPORT...")
    print("="*70 + "\n")
    
    review = generate_review_report(agent)
    
    print(json.dumps(review, indent=2))
    print(f"\nFull report saved to: /tmp/phoenix_review.json")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Default to demo if no args
        demo()
    else:
        main()
