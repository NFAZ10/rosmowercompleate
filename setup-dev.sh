#!/bin/bash

# Quick development setup for ROS mower project
echo "Setting up ROS 2 development environment..."

# Check if ROS 2 is installed
if ! command -v ros2 &> /dev/null; then
    echo "ROS 2 not found. Installing ROS 2 Jazzy..."
    
    # Add ROS 2 repository
    sudo apt update && sudo apt install -y curl gnupg lsb-release
    sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
    
    # Install ROS 2
    sudo apt update
    sudo apt install -y ros-jazzy-desktop-full python3-colcon-common-extensions
fi

# Source ROS 2
source /opt/ros/jazzy/setup.bash || source /opt/ros/humble/setup.bash || echo "No ROS 2 installation found"

# Install dependencies
sudo apt update && sudo apt install -y \
    python3-rosdep \
    python3-vcstool \
    build-essential \
    cmake \
    python3-serial \
    python3-yaml \
    python3-requests

# Initialize rosdep if not already done
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    sudo rosdep init
fi
rosdep update

echo "Development environment setup complete!"
echo ""
echo "To build the workspace:"
echo "  cd $(pwd)"
echo "  colcon build --symlink-install"
echo ""
echo "To run:"
echo "  source install/setup.bash"
echo "  ros2 launch rosmower launch_robot.launch.py"