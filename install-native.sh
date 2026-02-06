#!/bin/bash

# Native installation script for ROS mower project on ARM64/Raspberry Pi
set -e

echo "Setting up ROS 2 rosmower project natively..."
echo "Architecture: $(uname -m)"

# Check if we're on ARM64
ARCH=$(uname -m)
if [[ "$ARCH" != "aarch64" && "$ARCH" != "arm64" ]]; then
    echo "This script is optimized for ARM64/aarch64 systems (like Raspberry Pi)"
    echo "For x86_64 systems, consider using Docker instead"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
sudo apt update

# Install ROS 2 if not already installed
if ! command -v ros2 &> /dev/null; then
    echo "Installing ROS 2 Jazzy..."
    
    # Add ROS 2 repository
    sudo apt install -y curl gnupg lsb-release
    sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
    
    # Install ROS 2 (desktop version for ARM64)
    sudo apt update
    sudo apt install -y ros-jazzy-desktop python3-colcon-common-extensions
    
    # Install additional packages
    sudo apt install -y \
        ros-jazzy-joint-state-publisher \
        ros-jazzy-robot-state-publisher \
        ros-jazzy-xacro \
        ros-jazzy-tf2-tools \
        ros-jazzy-robot-localization \
        ros-jazzy-twist-mux \
        ros-jazzy-mavros \
        ros-jazzy-mavros-extras \
        ros-jazzy-mavros-msgs \
        ros-jazzy-sensor-msgs \
        ros-jazzy-nav-msgs \
        ros-jazzy-geometry-msgs \
        ros-jazzy-std-msgs \
        ros-jazzy-std-srvs \
        || echo "Some ROS packages not available, continuing..."
fi

# Install build dependencies
sudo apt install -y \
    python3-rosdep \
    python3-vcstool \
    build-essential \
    cmake \
    python3-serial \
    python3-yaml \
    python3-requests \
    python3-pip

# Initialize rosdep if not already done
if [ ! -f /etc/ros/rosdep/sources.list.d/20-default.list ]; then
    sudo rosdep init
fi
rosdep update

# Install workspace dependencies
echo "Installing workspace dependencies..."
rosdep install --from-paths src --ignore-src -r -y --skip-keys="hailo_msgs" || echo "Some dependencies could not be resolved, continuing..."

# Build the workspace
echo "Building workspace..."
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install

# Set up environment
if ! grep -q "source /opt/ros/jazzy/setup.bash" ~/.bashrc; then
    echo "source /opt/ros/jazzy/setup.bash" >> ~/.bashrc
fi

if ! grep -q "source $(pwd)/install/setup.bash" ~/.bashrc; then
    echo "source $(pwd)/install/setup.bash" >> ~/.bashrc
fi

if ! grep -q "export ROS_DOMAIN_ID=0" ~/.bashrc; then
    echo "export ROS_DOMAIN_ID=0" >> ~/.bashrc
fi

echo ""
echo "✅ Native installation complete!"
echo ""
echo "To use:"
echo "  source ~/.bashrc"
echo "  ros2 launch rosmower launch_robot.launch.py"
echo ""
echo "Or start a new terminal session."