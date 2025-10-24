#!/bin/bash
# Startup script to run both API server and poller

echo "Starting Polymarket Whale Tracker..."

# Create data directory if it doesn't exist
mkdir -p data

# Start API server in background
echo "Starting API server on port 8000..."
python -m uvicorn app:app --host 0.0.0.0 --port 8000 &
API_PID=$!

# Give API server time to start
sleep 2

# Start poller
echo "Starting background poller (5-minute intervals)..."
python poller.py &
POLLER_PID=$!

echo "Whale Tracker started successfully!"
echo "API Server PID: $API_PID"
echo "Poller PID: $POLLER_PID"
echo ""
echo "API available at: http://localhost:8000"
echo "Health check: http://localhost:8000/health"
echo "Recommendations: http://localhost:8000/api/recommendations"
echo ""
echo "Press Ctrl+C to stop..."

# Wait for both processes
wait
