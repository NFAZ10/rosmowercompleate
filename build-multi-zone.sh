#!/bin/bash
# Build script for Multi-Zone Route Management System
# This script builds the rosmower_msgs and rosmower packages within Docker

set -e

echo "========================================="
echo "Multi-Zone Route Management Build"
echo "========================================="

# Check if Docker image exists
if ! docker images | grep -q rosmower; then
    echo "ERROR: Docker image 'rosmower' not found!"
    echo "Please build the Docker image first:"
    echo "  ./build-docker.sh"
    exit 1
fi

echo "Building rosmower_msgs package (new message types)..."
docker run --rm \
    -v "$(pwd)":/ws \
    -w /ws \
    rosmower:latest \
    bash -c "source /opt/ros/humble/setup.bash && colcon build --packages-select rosmower_msgs --symlink-install"

echo ""
echo "Building rosmower package (new nodes and enhanced zone manager)..."
docker run --rm \
    -v "$(pwd)":/ws \
    -w /ws \
    rosmower:latest \
    bash -c "source /opt/ros/humble/setup.bash && source install/setup.bash && colcon build --packages-select rosmower --symlink-install"

echo ""
echo "========================================="
echo "Build Complete!"
echo "========================================="
echo ""
echo "New components built:"
echo "  ✓ 6 ROS2 message types (Route, RouteArray, ZoneGraph, etc.)"
echo "  ✓ Route Manager node (route_manager.py)"
echo "  ✓ Route Planner node (route_planner.py)"
echo "  ✓ Enhanced Zone Manager (zone_manager.py)"
echo "  ✓ Launch file (zone_and_route_management.launch.py)"
echo ""
echo "Next steps:"
echo "  1. Setup storage: ./setup_multi_zone_storage.sh"
echo "  2. Launch system in Docker:"
echo "     docker-compose up -d"
echo "     docker exec -it rosmower bash"
echo "     ros2 launch rosmower zone_and_route_management.launch.py"
echo "  3. Start web server: ./start-web-server.sh"
echo "  4. Open browser: http://<robot-ip>:8080/routes"
echo ""
