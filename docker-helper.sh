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
        if [ "$2" == "-d" ] || [ "$2" == "--detached" ]; then
            echo "Running ROS mower robot in detached mode..."
            docker-compose up -d rosmower
        else
            echo "Running ROS mower robot..."
            docker-compose up rosmower
        fi
        ;;
    "dev")
        if [ "$2" == "-d" ] || [ "$2" == "--detached" ]; then
            echo "Starting development container in detached mode..."
            docker-compose --profile dev run -d --rm dev bash
        else
            echo "Starting development container..."
            docker-compose --profile dev run --rm dev bash
        fi
        ;;
    "rviz")
        if [ "$2" == "-d" ] || [ "$2" == "--detached" ]; then
            echo "Starting RViz visualization in detached mode..."
            docker-compose --profile gui up -d rviz
        else
            echo "Starting RViz visualization..."
            docker-compose --profile gui up rviz
        fi
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
        echo "  run [-d|--detached] - Run the robot stack (optional: detached mode)"
        echo "  dev [-d|--detached] - Start development container (optional: detached mode)"
        echo "  rviz [-d|--detached] - Start RViz visualization (optional: detached mode)"
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
        echo "  $0 run -d          # Run the robot in detached mode"
        echo "  $0 dev             # Development mode"
        echo "  $0 dev -d          # Development mode in detached mode"
        ;;
esac