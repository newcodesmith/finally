#!/usr/bin/env bash
set -euo pipefail

CONTAINER_NAME="finally-app"

if docker ps -q -f name="$CONTAINER_NAME" | grep -q .; then
    docker stop "$CONTAINER_NAME"
    docker rm "$CONTAINER_NAME"
    echo "FinAlly stopped and container removed."
    echo "Data volume 'finally-data' preserved. Run 'docker volume rm finally-data' to delete data."
else
    # Container might exist but be stopped
    docker rm "$CONTAINER_NAME" 2>/dev/null && echo "Removed stopped container." || echo "No running FinAlly container found."
fi
