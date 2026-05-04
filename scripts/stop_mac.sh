#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

echo "Stopping FinAlly..."
docker compose down

echo "FinAlly stopped. Data is preserved in the Docker volume."
echo "To remove data: docker volume rm finally_finally-data"
