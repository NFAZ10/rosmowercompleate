#!/bin/bash
# Test script for stereo cameras - Run INSIDE Docker container

echo "=== Stereo Camera Test ==="
echo ""

# Check cameras
echo "1. Checking camera devices..."
ls -la /dev/video* 2>/dev/null
echo ""

# List detected cameras
echo "2. Camera detection details:"
v4l2-ctl --list-devices 2>/dev/null
echo ""

# Build package
echo "3. Building stereo_camera_viewer package..."
cd /mnt/nova_ssd/rosmowercompleate
colcon build --packages-select stereo_camera_viewer --symlink-install
echo ""

# Source workspace
echo "4. Sourcing workspace..."
source install/setup.bash
echo ""

# Launch cameras
echo "5. Launching stereo cameras..."
echo "   Published topics:"
echo "   - /stereo/left/image_raw"
echo "   - /stereo/right/image_raw"
echo "   - /stereo/left/camera_info"
echo "   - /stereo/right/camera_info"
echo ""
echo "   View in another terminal with:"
echo "   - rviz2"
echo "   - ros2 run rqt_image_view rqt_image_view /stereo/left/image_raw"
echo ""
echo "Press Ctrl+C to stop..."
echo ""

ros2 launch stereo_camera_viewer stereo_cameras.launch.py
