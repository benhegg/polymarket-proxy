#!/bin/bash
# Railway startup script - runs from repo root

echo "🚂 Starting Polymarket Whale Tracker on Railway..."

# Navigate to python backend
cd python-backend

# Create data directory
mkdir -p data

echo "📦 Installing dependencies..."
pip install -r requirements.txt

echo "🚀 Starting API server and poller..."

# Start API server in background
python -m uvicorn app:app --host 0.0.0.0 --port ${PORT:-8000} &
API_PID=$!

# Give API time to start
sleep 3

# Start poller
python poller.py &
POLLER_PID=$!

echo "✅ Started successfully!"
echo "   API Server PID: $API_PID"
echo "   Poller PID: $POLLER_PID"

# Keep container alive
wait
