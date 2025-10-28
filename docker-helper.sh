#!/bin/bash

# ROS Mower Docker Helper Script
set -e

# Ensure Docker daemon is running
if ! docker info >/dev/null 2>&1; then
    echo "Starting Docker daemon..."
    ./start-docker.sh
fi

case "$1" in
    "build")
        echo "Building ROS mower Docker image..."
        # Pass image type argument (slim or desktop, defaults to desktop)
        ./build-docker.sh "$2"
        ;;
    "build-slim")
        echo "Building slim ROS mower Docker image..."
        ./build-docker.sh slim
        ;;
    "build-desktop")
        echo "Building desktop ROS mower Docker image..."
        ./build-docker.sh desktop
        ;;
    "run")
        echo "Running ROS mower robot..."
        docker-compose up rosmower
        ;;
    "dev")
        echo "Starting development container..."
        docker-compose --profile dev run --rm dev bash
        ;;
    "rviz")
        echo "Starting RViz visualization..."
        docker-compose --profile gui up rviz
        ;;
    "shell")
        echo "Opening shell in running container..."
        docker exec -it rosmower_robot bash
        ;;
    "logs")
        echo "Showing container logs..."
        docker logs rosmower_robot
        ;;
    "stop")
        echo "Stopping all containers..."
        docker-compose down
        ;;
    "clean")
        echo "Cleaning up containers and images..."
        docker-compose down
        docker rmi rosmower:latest 2>/dev/null || true
        ;;
    "status")
        echo "Docker status:"
        docker ps -a --filter "name=rosmower"
        echo ""
        echo "Images:"
        docker images | grep rosmower || echo "No rosmower images found"
        ;;
    *)
        echo "ROS Mower Docker Helper"
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  build [TYPE]    - Build the Docker image (TYPE: slim or desktop, default: desktop)"
        echo "  build-slim      - Build slim image (ros-core, minimal ROS)"
        echo "  build-desktop   - Build desktop image (with GUI components)"
        echo "  run             - Run the robot stack"
        echo "  dev     - Start development container"
        echo "  rviz    - Start RViz visualization"
        echo "  shell   - Open shell in running container"
        echo "  logs    - Show container logs"
        echo "  stop    - Stop all containers"
        echo "  clean   - Clean up containers and images"
        echo "  status  - Show Docker status"
        echo ""
        echo "Examples:"
        echo "  $0 build           # Build desktop image (default)"
        echo "  $0 build slim      # Build slim image"
        echo "  $0 build-slim      # Build slim image"
        echo "  $0 build-desktop   # Build desktop image"
        echo "  $0 run             # Run the robot"
        echo "  $0 dev             # Development mode"
        ;;
esac