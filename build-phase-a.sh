#!/bin/bash
# Build ROS packages in a temporary Docker container

set -e

echo "Building ROS packages..."
echo "======================="

# Run build in a temporary container
docker run --rm \
    -v /mnt/nova_ssd/rosmowercompleate:/ws \
    -w /ws \
    rosmower:latest \
    bash -c "source /opt/ros/humble/setup.bash && colcon build --packages-select rosmower_msgs rosmower --symlink-install"

echo ""
echo "Build complete!"
echo "To test the nodes, start the robot container with:"
echo "  ./docker-helper.sh run"
