#!/usr/bin/env python3
"""
Project Phoenix: Unstable Application
This app simulates real-world issues: crashes, OOM, port conflicts, permission issues
"""

import os
import sys
import time
import json
import random
import psutil
import signal
from datetime import datetime
from pathlib import Path

# State file for the app to track restarts and failures
STATE_FILE = Path("/tmp/phoenix_app_state.json")
LOG_FILE = Path("/tmp/phoenix_app.log")
CRASH_TRIGGER_FILE = Path("/tmp/phoenix_crash_trigger")


def log_event(event_type, message, metadata=None):
    """Log events to both console and file"""
    timestamp = datetime.now().isoformat()
    log_entry = {
        "timestamp": timestamp,
        "type": event_type,
        "message": message,
        "metadata": metadata or {},
    }
    
    print(json.dumps(log_entry))
    
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(log_entry) + "\n")


def get_app_state():
    """Retrieve app state"""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"restarts": 0, "crashes": 0, "uptime": 0}


def update_app_state(state):
    """Update app state"""
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def simulate_memory_pressure():
    """Simulate high memory usage"""
    # Allocate memory (but not too much to actually crash the system)
    try:
        large_list = [0] * (100 * 1024 * 1024 // 8)  # ~100MB
        time.sleep(2)
        del large_list
    except MemoryError:
        log_event("ERROR", "Memory allocation failed", {"type": "OOM"})
        raise


def simulate_port_conflict():
    """Simulate port already in use error"""
    PORT = 5000
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(("localhost", PORT))
        sock.close()
        
        if result == 0:
            log_event("ERROR", f"Port {PORT} already in use", {"port": PORT, "type": "PORT_CONFLICT"})
            raise RuntimeError(f"Port {PORT} is already in use")
    except Exception as e:
        log_event("ERROR", str(e), {"type": "PORT_CONFLICT"})
        raise


def simulate_permission_error():
    """Simulate permission denied error"""
    restricted_file = "/root/.ssh/id_rsa"
    try:
        with open(restricted_file, "r") as f:
            f.read()
    except PermissionError:
        log_event("ERROR", f"Permission denied: {restricted_file}", {"type": "PERMISSION_ERROR", "file": restricted_file})
        raise
    except FileNotFoundError:
        pass  # Expected on most systems


def simulate_disk_full():
    """Simulate disk full error"""
    temp_file = Path("/tmp/phoenix_large_file.bin")
    try:
        # Try to write a large file
        with open(temp_file, "wb") as f:
            f.write(b"x" * (5 * 1024 * 1024 * 1024))  # 5GB
    except OSError as e:
        log_event("ERROR", f"Disk I/O error: {str(e)}", {"type": "DISK_FULL"})
        if temp_file.exists():
            temp_file.unlink()
        raise


def run_app_loop(duration=60):
    """Main application loop"""
    state = get_app_state()
    state["restarts"] += 1
    
    log_event("APP_START", f"Application started (restart #{state['restarts']})", {"restarts": state["restarts"]})
    
    start_time = time.time()
    error_sequence = [
        ("memory", simulate_memory_pressure),
        ("port", simulate_port_conflict),
        ("permission", simulate_permission_error),
    ]
    
    # Randomly decide what error to trigger
    should_crash = random.random() < 0.3  # 30% chance of crash
    
    # Check if crash was manually triggered
    if CRASH_TRIGGER_FILE.exists():
        should_crash = True
        CRASH_TRIGGER_FILE.unlink()
        log_event("CRASH_TRIGGERED", "Manual crash trigger detected")
    
    if should_crash:
        error_type, error_func = random.choice(error_sequence)
        log_event("SIMULATING_ERROR", f"Simulating {error_type} error", {"error_type": error_type})
        
        try:
            error_func()
        except Exception as e:
            state["crashes"] += 1
            update_app_state(state)
            log_event("CRASH", f"Application crashed: {str(e)}", 
                     {"error_type": error_type, "total_crashes": state["crashes"]})
            sys.exit(1)
    
    # Normal operation loop
    try:
        while time.time() - start_time < duration:
            log_event("APP_HEALTHY", "Application running normally", 
                     {"uptime_seconds": int(time.time() - start_time)})
            time.sleep(5)
        
        update_app_state(state)
        log_event("APP_GRACEFUL_SHUTDOWN", "Application shutting down normally")
        sys.exit(0)
    
    except KeyboardInterrupt:
        log_event("APP_INTERRUPTED", "Application interrupted by user")
        sys.exit(0)


def signal_handler(signum, frame):
    """Handle signals"""
    log_event("SIGNAL_RECEIVED", f"Signal {signum} received")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Create log file if it doesn't exist
    LOG_FILE.touch(exist_ok=True)
    
    duration = int(sys.argv[1]) if len(sys.argv) > 1 else 60
    run_app_loop(duration)
