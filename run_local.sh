#!/bin/bash
# ===================================
# File: run_local.sh
# ===================================
# Script to run the application locally without Docker.
# Prerequisites: Redis running on localhost:6379, Python 3.12, pip.

set -euo pipefail

echo "========================================="
echo " Smart URL Analyzer - Local Development"
echo "========================================="

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "[1/5] Creating virtual environment..."
    python3.12 -m venv venv
else
    echo "[1/5] Virtual environment already exists."
fi

# Activate virtual environment
echo "[2/5] Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "[3/5] Installing dependencies..."
pip install --quiet -r requirements.txt

# Create logs directory
mkdir -p logs

# Export environment variables for local development
export REDIS_URL="redis://localhost:6379/0"
export CELERY_BROKER_URL="redis://localhost:6379/1"
export CELERY_RESULT_BACKEND="redis://localhost:6379/2"
export LOG_LEVEL="DEBUG"
export LOG_FILE="logs/app.log"

# Start Celery worker in background
echo "[4/5] Starting Celery worker..."
celery -A app.celery_app:celery_app worker --loglevel=info --concurrency=2 &
CELERY_PID=$!
echo "       Celery worker PID: $CELERY_PID"

# Give Celery a moment to connect
sleep 2

# Start FastAPI server
echo "[5/5] Starting FastAPI server on http://localhost:8000"
echo "       Swagger docs: http://localhost:8000/docs"
echo "========================================="
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Cleanup: kill Celery worker on exit
trap "echo 'Stopping Celery worker...'; kill $CELERY_PID 2>/dev/null" EXIT
