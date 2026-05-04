#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
CONTAINER_NAME="finally-app"

cd "$PROJECT_DIR"

# Check for .env file
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Copying from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo "Created .env from .env.example. Edit it to add your API keys."
    else
        echo "Error: Neither .env nor .env.example found."
        exit 1
    fi
fi

echo "Building and starting FinAlly..."
docker compose up --build -d

echo ""
echo "FinAlly is running at: http://localhost:8000"
echo "To stop: ./scripts/stop_mac.sh"

# Open browser (optional, non-fatal)
if command -v open &> /dev/null; then
    sleep 2
    open "http://localhost:8000" 2>/dev/null || true
fi
