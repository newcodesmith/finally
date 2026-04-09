#!/usr/bin/env bash
# FinAlly — Start script for macOS/Linux
# Usage: ./scripts/start_mac.sh [--build] [--open]
#   --build   Force rebuild the Docker image
#   --open    Open browser after starting

set -euo pipefail

CONTAINER_NAME="finally"

# Wait for Docker daemon to be ready
MAX_WAIT=30
WAITED=0
while ! docker info >/dev/null 2>&1; do
    if [ "$WAITED" -eq 0 ]; then
        echo "Waiting for Docker daemon to start..."
    fi
    sleep 1
    WAITED=$((WAITED + 1))
    if [ "$WAITED" -ge "$MAX_WAIT" ]; then
        echo "Error: Docker daemon not available after ${MAX_WAIT}s."
        echo "Please start Docker Desktop and try again."
        exit 1
    fi
done
if [ "$WAITED" -gt 0 ]; then
    echo "Docker is ready."
fi
IMAGE_NAME="finally"
VOLUME_NAME="finally-data"
PORT=8000
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

# Parse flags
FORCE_BUILD=false
OPEN_BROWSER=false
for arg in "$@"; do
    case "$arg" in
        --build) FORCE_BUILD=true ;;
        --open)  OPEN_BROWSER=true ;;
        *)       echo "Unknown flag: $arg"; echo "Usage: $0 [--build] [--open]"; exit 1 ;;
    esac
done

# Stop existing container if running (idempotent)
if docker ps -q -f name="^${CONTAINER_NAME}$" | grep -q .; then
    echo "Stopping existing ${CONTAINER_NAME} container..."
    docker stop "$CONTAINER_NAME" >/dev/null 2>&1
    docker rm "$CONTAINER_NAME" >/dev/null 2>&1
elif docker ps -aq -f name="^${CONTAINER_NAME}$" | grep -q .; then
    echo "Removing stopped ${CONTAINER_NAME} container..."
    docker rm "$CONTAINER_NAME" >/dev/null 2>&1
fi

# Build image if it doesn't exist or --build flag is passed
if [ "$FORCE_BUILD" = true ] || ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo "Building Docker image..."
    docker build -t "$IMAGE_NAME" "$PROJECT_DIR"
    echo "Build complete."
else
    echo "Using existing Docker image. Pass --build to rebuild."
fi

# Check for .env file
ENV_FILE_FLAG=""
if [ -f "$PROJECT_DIR/.env" ]; then
    ENV_FILE_FLAG="--env-file $PROJECT_DIR/.env"
else
    echo "Warning: No .env file found. LLM chat will not work without OPENROUTER_API_KEY."
    echo "Copy .env.example to .env and add your API key:"
    echo "  cp .env.example .env"
fi

# Run container
echo "Starting ${CONTAINER_NAME}..."
docker run -d \
    --name "$CONTAINER_NAME" \
    -v "${VOLUME_NAME}:/app/db" \
    -p "${PORT}:8000" \
    -e "DB_PATH=/app/db/finally.db" \
    $ENV_FILE_FLAG \
    "$IMAGE_NAME"

echo ""
echo "========================================="
echo "  FinAlly is running!"
echo "  http://localhost:${PORT}"
echo "========================================="
echo ""

# Optionally open browser
if [ "$OPEN_BROWSER" = true ]; then
    if command -v open >/dev/null 2>&1; then
        open "http://localhost:${PORT}"
    elif command -v xdg-open >/dev/null 2>&1; then
        xdg-open "http://localhost:${PORT}"
    fi
fi
