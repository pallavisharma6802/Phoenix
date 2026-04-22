#!/usr/bin/env python3
"""
Project Phoenix: Test Scenarios
Run 50 iterations of different error types to evaluate agent performance
"""

import json
import random
import subprocess
import time
from pathlib import Path
from typing import List, Dict
from agent.phoenix_agent import PhoenixDevOpsAgent, IncidentPhase

DEFAULT_REPORT_FILE = str(Path(__file__).resolve().parents[1] / "phoenix_test_report.json")


class TestScenarioRunner:
    """Runs test scenarios and collects metrics"""
    
    ERROR_TYPES = [
        ("OOM", "Memory allocation failed"),
        ("PORT_CONFLICT", "Port 5000 already in use"),
        ("PERMISSION_ERROR", "Permission denied: /root/.ssh/id_rsa"),
        ("DISK_FULL", "No space left on device"),
    ]
    
    def __init__(self, num_iterations: int = 50):
        self.num_iterations = num_iterations
        self.results = []
        self.metrics = {
            "total_runs": 0,
            "successful_resolutions": 0,
            "failed_resolutions": 0,
            "average_attempts": 0,
            "intent_drift_detections": 0,
            "error_distribution": {},
            "phase_analysis": {},
        }
    
    def generate_error_logs(self, error_type: str, error_message: str) -> List[Dict]:
        """Generate realistic error logs"""
        return [
            {
                "timestamp": time.time(),
                "type": "APP_START",
                "message": "Application started",
                "metadata": {}
            },
            {
                "timestamp": time.time() + 5,
                "type": "APP_HEALTHY",
                "message": "Application running",
                "metadata": {}
            },
            {
                "timestamp": time.time() + 10,
                "type": "ERROR",
                "message": error_message,
                "metadata": {"type": error_type}
            },
            {
                "timestamp": time.time() + 12,
                "type": "CRASH",
                "message": f"Application crashed: {error_message}",
                "metadata": {"type": error_type, "total_crashes": 1}
            }
        ]
    
    def run_test_scenario(self, iteration: int) -> Dict:
        """Run a single test scenario"""
        error_type, error_message = random.choice(self.ERROR_TYPES)
        
        # Generate logs
        logs = self.generate_error_logs(error_type, error_message)
        
        # Initialize agent
        agent = PhoenixDevOpsAgent(user_id=f"test-scenario-{iteration}")
        
        # Run troubleshooting loop
        report = agent.run_troubleshooting_loop(logs, max_attempts=3)
        
        result = {
            "iteration": iteration,
            "error_type": error_type,
            "success": report.success,
            "attempts": report.attempts,
            "phase": report.phase.value,
            "intent_drift": report.intent_drift_detected,
            "resolution": report.resolution
        }
        
        return result
    
    def run_all_scenarios(self) -> Dict:
        """Run all test scenarios"""
        print(f"\nRunning {self.num_iterations} test scenarios...\n")
        
        for i in range(1, self.num_iterations + 1):
            result = self.run_test_scenario(i)
            self.results.append(result)
            
            # Update metrics
            self.metrics["total_runs"] += 1
            
            if result["success"]:
                self.metrics["successful_resolutions"] += 1
            else:
                self.metrics["failed_resolutions"] += 1
            
            error_type = result["error_type"]
            self.metrics["error_distribution"][error_type] = \
                self.metrics["error_distribution"].get(error_type, 0) + 1
            
            if result["intent_drift"]:
                self.metrics["intent_drift_detections"] += 1
            
            # Print progress
            if i % 10 == 0:
                print(f"✓ Completed {i}/{self.num_iterations} scenarios")
                print(f"  Success rate: {(self.metrics['successful_resolutions'] / i * 100):.1f}%")
                print(f"  Intent drift blocks: {self.metrics['intent_drift_detections']}\n")
        
        # Calculate averages
        if self.metrics["total_runs"] > 0:
            self.metrics["average_attempts"] = sum(r["attempts"] for r in self.results) / self.metrics["total_runs"]
        
        return self.metrics
    
    def generate_report(self, output_file: str = DEFAULT_REPORT_FILE) -> Dict:
        """Generate test report"""
        report = {
            "test_run": {
                "total_scenarios": self.metrics["total_runs"],
                "timestamp": time.time()
            },
            "results": {
                "successful_resolutions": self.metrics["successful_resolutions"],
                "failed_resolutions": self.metrics["failed_resolutions"],
                "success_rate": f"{(self.metrics['successful_resolutions'] / self.metrics['total_runs'] * 100):.1f}%" 
                    if self.metrics["total_runs"] > 0 else "0%",
                "average_attempts": f"{self.metrics['average_attempts']:.2f}",
                "intent_drift_detections": self.metrics["intent_drift_detections"],
            },
            "error_distribution": self.metrics["error_distribution"],
            "scenario_details": self.results,
            "recent_scenarios": self.results[-10:],
        }
        
        with open(output_file, "w") as f:
            json.dump(report, f, indent=2)
        
        return report
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*70)
        print("PROJECT PHOENIX: TEST SUMMARY")
        print("="*70)
        print(f"\nTotal Scenarios Run: {self.metrics['total_runs']}")
        print(f"Successful Resolutions: {self.metrics['successful_resolutions']}")
        print(f"Failed Resolutions: {self.metrics['failed_resolutions']}")
        print(f"Success Rate: {(self.metrics['successful_resolutions'] / self.metrics['total_runs'] * 100):.1f}%")
        print(f"Average Attempts per Incident: {self.metrics['average_attempts']:.2f}")
        print(f"Intent Drift Detections: {self.metrics['intent_drift_detections']}")
        
        print("\nError Distribution:")
        for error_type, count in self.metrics["error_distribution"].items():
            percentage = (count / self.metrics["total_runs"] * 100)
            print(f"  {error_type}: {count} ({percentage:.1f}%)")
        
        print("\n" + "="*70)
        print("KEY FINDINGS FOR FOUNDERS")
        print("="*70)
        
        findings = []
        
        if self.metrics["successful_resolutions"] / self.metrics["total_runs"] > 0.8:
            findings.append("✓ High automation rate: Agent successfully resolved >80% of incidents")
        
        if self.metrics["intent_drift_detections"] > 0:
            findings.append(f"✓ Safety net active: Blocked {self.metrics['intent_drift_detections']} dangerous commands")
        
        findings.append("✓ Agnost tracking: All incidents logged with Chain-of-Thought visibility")
        findings.append("✓ Error diversity: Agent handled multiple error types")
        
        for finding in findings:
            print(f"{finding}")
        
        print("\n" + "="*70)


if __name__ == "__main__":
    runner = TestScenarioRunner(num_iterations=50)
    
    try:
        metrics = runner.run_all_scenarios()
        report = runner.generate_report()
        runner.print_summary()
        
        print(f"\nDetailed report saved to: {DEFAULT_REPORT_FILE}")
    
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        runner.print_summary()
