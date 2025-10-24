#!/bin/bash

# ROS 2 Rosmower Docker Build and Run Script
# This script provides convenient commands to build and run the rosmower Docker containers

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}$1${NC}"
}

# Function to check if Docker is installed and running
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! docker info &> /dev/null; then
        print_error "Docker is not running. Please start Docker first."
        exit 1
    fi
}

# Function to build the Docker image
build_image() {
    print_header "=== Building ROS 2 Rosmower Docker Image ==="
    print_status "Building image with tag 'rosmower:latest'..."
    
    docker build -t rosmower:latest .
    
    if [ $? -eq 0 ]; then
        print_status "Docker image built successfully!"
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
}

# Function to run the robot stack
run_robot() {
    print_header "=== Running Rosmower Robot Stack ==="
    print_status "Starting robot container..."
    
    # Allow X11 forwarding for GUI applications
    xhost +local:docker > /dev/null 2>&1 || true
    
    docker-compose up rosmower
}

# Function to run development container
run_dev() {
    print_header "=== Starting Development Container ==="
    print_status "Starting development container with workspace mounted..."
    
    xhost +local:docker > /dev/null 2>&1 || true
    
    docker-compose --profile dev up -d dev
    docker-compose exec dev bash
}

# Function to run RViz
run_rviz() {
    print_header "=== Starting RViz ==="
    print_status "Starting RViz container..."
    
    xhost +local:docker > /dev/null 2>&1 || true
    
    docker-compose --profile gui up rviz
}

# Function to stop all containers
stop_containers() {
    print_header "=== Stopping All Containers ==="
    print_status "Stopping rosmower containers..."
    
    docker-compose down
    docker-compose --profile dev down
    docker-compose --profile gui down
}

# Function to clean up Docker images and containers
cleanup() {
    print_header "=== Cleaning Up Docker Resources ==="
    print_warning "This will remove all rosmower containers and images"
    read -p "Are you sure? (y/N): " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        print_status "Removing containers..."
        docker-compose down --rmi all --volumes --remove-orphans
        
        print_status "Removing rosmower images..."
        docker images | grep rosmower | awk '{print $3}' | xargs -r docker rmi
        
        print_status "Cleanup completed!"
    else
        print_status "Cleanup cancelled"
    fi
}

# Function to show logs
show_logs() {
    print_header "=== Container Logs ==="
    docker-compose logs -f
}

# Function to check system compatibility for Jetson
check_jetson_compatibility() {
    print_header "=== Jetson Compatibility Check ==="
    
    # Check if we can build ARM images
    if docker buildx ls | grep -q "linux/arm64"; then
        print_status "Multi-architecture build support detected"
        print_status "Ready for Jetson deployment"
    else
        print_warning "Multi-architecture build not configured"
        print_status "Run: docker buildx create --use --name multi-arch --driver docker-container"
    fi
    
    # Check image size
    if docker images rosmower:latest --format "table {{.Size}}" | tail -n 1 | grep -q "GB"; then
        size=$(docker images rosmower:latest --format "table {{.Size}}" | tail -n 1)
        print_warning "Image size: $size - consider optimization for Jetson"
    fi
}

# Function to build for Jetson (ARM64)
build_jetson() {
    print_header "=== Building for Jetson (ARM64) ==="
    print_status "Building multi-architecture image for Jetson..."
    
    # Ensure buildx is available
    docker buildx create --use --name multi-arch --driver docker-container 2>/dev/null || true
    
    # Build for ARM64
    docker buildx build --platform linux/arm64 -t rosmower:jetson --load .
    
    if [ $? -eq 0 ]; then
        print_status "Jetson image built successfully!"
        print_status "To save for transfer: docker save rosmower:jetson | gzip > rosmower_jetson.tar.gz"
    else
        print_error "Failed to build Jetson image"
        exit 1
    fi
}

# Function to save image for transfer
save_image() {
    print_header "=== Saving Docker Image ==="
    print_status "Saving rosmower:latest to tar.gz file..."
    
    docker save rosmower:latest | gzip > rosmower_$(date +%Y%m%d).tar.gz
    
    print_status "Image saved as rosmower_$(date +%Y%m%d).tar.gz"
    print_status "To load on target system: docker load < rosmower_$(date +%Y%m%d).tar.gz"
}

# Function to show usage
show_usage() {
    print_header "=== ROS 2 Rosmower Docker Management Script ==="
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  build          Build the Docker image"
    echo "  run            Run the robot stack"
    echo "  dev            Start development container"
    echo "  rviz           Start RViz container"
    echo "  stop           Stop all containers"
    echo "  logs           Show container logs"
    echo "  cleanup        Remove all containers and images"
    echo "  jetson-check   Check Jetson deployment compatibility"
    echo "  build-jetson   Build ARM64 image for Jetson"
    echo "  save           Save image to tar.gz file"
    echo "  help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 build && $0 run    # Build and run robot"
    echo "  $0 dev                # Start development environment"
    echo "  $0 build-jetson       # Build for Jetson deployment"
}

# Main script logic
case "$1" in
    build)
        check_docker
        build_image
        ;;
    run)
        check_docker
        run_robot
        ;;
    dev)
        check_docker
        run_dev
        ;;
    rviz)
        check_docker
        run_rviz
        ;;
    stop)
        check_docker
        stop_containers
        ;;
    logs)
        check_docker
        show_logs
        ;;
    cleanup)
        check_docker
        cleanup
        ;;
    jetson-check)
        check_docker
        check_jetson_compatibility
        ;;
    build-jetson)
        check_docker
        build_jetson
        ;;
    save)
        check_docker
        save_image
        ;;
    help|--help|-h)
        show_usage
        ;;
    *)
        print_error "Unknown command: $1"
        echo ""
        show_usage
        exit 1
        ;;
esac