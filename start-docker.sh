#!/bin/bash

# Script to start Docker daemon in WSL
echo "Starting Docker daemon for WSL..."

# Check if Docker daemon is already running
if docker info >/dev/null 2>&1; then
    echo "Docker daemon is already running."
    exit 0
fi

# Start Docker daemon
echo "Starting Docker daemon..."
sudo dockerd > /tmp/dockerd.log 2>&1 &
DOCKER_PID=$!

# Wait for Docker to be ready
echo "Waiting for Docker daemon to be ready..."
for i in {1..30}; do
    if docker info >/dev/null 2>&1; then
        echo "Docker daemon is ready!"
        echo "Docker daemon PID: $DOCKER_PID"
        echo "Docker daemon logs are in /tmp/dockerd.log"
        exit 0
    fi
    sleep 1
done

echo "Docker daemon failed to start within 30 seconds."
echo "Check logs: tail -f /tmp/dockerd.log"
exit 1