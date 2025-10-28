#!/bin/bash

# Auto-detect architecture and build appropriate Docker image
# Usage: build-docker.sh [IMAGE_TYPE]
# IMAGE_TYPE: 'slim' for base image (no desktop) or 'desktop' for full desktop (default: desktop)
set -e

# Parse image type argument
IMAGE_TYPE=${1:-desktop}
if [[ "$IMAGE_TYPE" != "slim" && "$IMAGE_TYPE" != "desktop" ]]; then
    echo "Invalid image type: $IMAGE_TYPE"
    echo "Valid options: 'slim' (base image) or 'desktop' (full desktop)"
    exit 1
fi

# Convert slim to ros-core for ROS image naming
ROS_IMAGE_TYPE=$IMAGE_TYPE
if [[ "$IMAGE_TYPE" == "slim" ]]; then
    ROS_IMAGE_TYPE="ros-core"
fi

echo "Building $IMAGE_TYPE image (using ros:humble-$ROS_IMAGE_TYPE)"

# Detect architecture
ARCH=$(uname -m)
echo "Detected architecture: $ARCH"

# Choose appropriate Dockerfile and image tag
if [[ "$ARCH" == "aarch64" || "$ARCH" == "arm64" ]]; then
    echo "Using ARM64 Dockerfile..."
    DOCKERFILE="Dockerfile.arm64"
    IMAGE_TAG="rosmower:latest-arm64-$IMAGE_TYPE"
elif [[ "$ARCH" == "x86_64" ]]; then
    echo "Using x86_64 Dockerfile..."
    DOCKERFILE="Dockerfile"
    IMAGE_TAG="rosmower:latest-$IMAGE_TYPE"
else
    echo "Unsupported architecture: $ARCH"
    echo "Supported architectures: x86_64, aarch64/arm64"
    exit 1
fi

echo "Building Docker image with $DOCKERFILE -> $IMAGE_TAG"

# Build the image with IMAGE_TYPE build argument (using BuildKit for better performance)
docker build \
    --build-arg IMAGE_TYPE="$ROS_IMAGE_TYPE" \
    -f "$DOCKERFILE" \
    -t "$IMAGE_TAG" .

# Also tag as 'latest' for consistency
docker tag "$IMAGE_TAG" "rosmower:latest"

echo "Build completed successfully!"
echo "Image: $IMAGE_TAG"
echo "Also tagged as: rosmower:latest"