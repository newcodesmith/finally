#!/usr/bin/env bash
set -euo pipefail

IMAGE_NAME="finally"
CONTAINER_NAME="finally-app"
VOLUME_NAME="finally-data"
PORT=8000

# Build if --build flag passed or image doesn't exist
if [[ "${1:-}" == "--build" ]] || ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
    echo "Building Docker image..."
    docker build -t "$IMAGE_NAME" .
fi

# Stop existing container if running (idempotent)
docker rm -f "$CONTAINER_NAME" 2>/dev/null || true

# Determine env file flag
DOCKER_ARGS=()
if [[ -f .env ]]; then
    DOCKER_ARGS+=(--env-file .env)
fi

# Run container
docker run -d \
    --name "$CONTAINER_NAME" \
    -v "$VOLUME_NAME:/app/db" \
    -p "$PORT:8000" \
    "${DOCKER_ARGS[@]}" \
    "$IMAGE_NAME"

echo ""
echo "FinAlly is running at http://localhost:$PORT"
echo "  Container: $CONTAINER_NAME"
echo "  Volume:    $VOLUME_NAME (SQLite data persists here)"
echo ""
echo "Stop with: ./scripts/stop_mac.sh"
