#!/bin/bash

# Auto-detect architecture and build appropriate Docker image
set -e

# Detect architecture
ARCH=$(uname -m)
echo "Detected architecture: $ARCH"

# Choose appropriate Dockerfile
if [[ "$ARCH" == "aarch64" || "$ARCH" == "arm64" ]]; then
    echo "Using ARM64 Dockerfile..."
    DOCKERFILE="Dockerfile.arm64"
    IMAGE_TAG="rosmower:latest-arm64"
elif [[ "$ARCH" == "x86_64" ]]; then
    echo "Using x86_64 Dockerfile..."
    DOCKERFILE="Dockerfile"
    IMAGE_TAG="rosmower:latest"
else
    echo "Unsupported architecture: $ARCH"
    echo "Supported architectures: x86_64, aarch64/arm64"
    exit 1
fi

echo "Building Docker image with $DOCKERFILE -> $IMAGE_TAG"

# Build the image
DOCKER_BUILDKIT=0 docker build -f "$DOCKERFILE" -t "$IMAGE_TAG" .

# Also tag as 'latest' for consistency
docker tag "$IMAGE_TAG" "rosmower:latest"

echo "Build completed successfully!"
echo "Image: $IMAGE_TAG"