#!/usr/bin/env bash
# FinAlly — Stop script for macOS/Linux
# Stops and removes the container but preserves the data volume.

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

if docker ps -q -f name="^${CONTAINER_NAME}$" | grep -q .; then
    echo "Stopping ${CONTAINER_NAME}..."
    docker stop "$CONTAINER_NAME" >/dev/null 2>&1
    docker rm "$CONTAINER_NAME" >/dev/null 2>&1
    echo "Stopped and removed container. Data volume preserved."
elif docker ps -aq -f name="^${CONTAINER_NAME}$" | grep -q .; then
    echo "Removing stopped ${CONTAINER_NAME} container..."
    docker rm "$CONTAINER_NAME" >/dev/null 2>&1
    echo "Removed container. Data volume preserved."
else
    echo "No ${CONTAINER_NAME} container found. Nothing to do."
fi
