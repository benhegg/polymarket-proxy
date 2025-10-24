#!/usr/bin/env python3
"""
Startup script for Render - runs both API server and poller
"""
import os
import sys
import subprocess
import signal
import time

# Change to python-backend directory
os.chdir('/opt/render/project/src/python-backend')

# Get port from environment
port = os.environ.get('PORT', '8000')

print(f"🐍 Python version: {sys.version}")
print(f"🚀 Starting Polymarket Whale Tracker on port {port}")

# Start API server
api_process = subprocess.Popen([
    sys.executable, '-m', 'uvicorn',
    'app:app',
    '--host', '0.0.0.0',
    '--port', port
])

# Wait a moment for API to start
time.sleep(3)

# Start poller
poller_process = subprocess.Popen([
    sys.executable, 'poller.py'
])

print(f"✅ API running on port {port} (PID: {api_process.pid})")
print(f"✅ Poller running (PID: {poller_process.pid})")

# Handle shutdown gracefully
def shutdown(signum, frame):
    print("Shutting down...")
    api_process.terminate()
    poller_process.terminate()
    sys.exit(0)

signal.signal(signal.SIGTERM, shutdown)
signal.signal(signal.SIGINT, shutdown)

# Keep running - monitor both processes
try:
    while True:
        time.sleep(1)
        # Check if processes are still alive
        if api_process.poll() is not None:
            print(f"⚠️ API process died with code {api_process.returncode}")
        if poller_process.poll() is not None:
            print(f"⚠️ Poller process died with code {poller_process.returncode}")
except KeyboardInterrupt:
    shutdown(None, None)
