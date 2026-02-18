#!/bin/bash

# Quick Start Guide for Upgraded Sensors
# Run this after upgrading to RPlidar C1 and Stereo CSI Cameras

echo "================================================"
echo "  Upgraded Sensor Quick Start"
echo "  RPlidar C1 + Stereo CSI Cameras (IMX219)"
echo "================================================"
echo ""

# Step 1: Verify hardware
echo "[1/5] Verifying hardware detection..."
echo ""
echo "LIDAR:"
ls -l /dev/ttyUSB0 2>/dev/null && echo "  ✓ RPlidar C1 detected" || echo "  ✗ LIDAR not found"
ls -l /dev/serial/by-id/*CP2102* 2>/dev/null | head -1

echo ""
echo "Cameras:"
ls -l /dev/video1 2>/dev/null && echo "  ✓ Left camera (CAM1) detected" || echo "  ✗ Left camera not found"
ls -l /dev/video2 2>/dev/null && echo "  ✓ Right camera (CAM0) detected" || echo "  ✗ Right camera not found"

echo ""
echo "[2/5] Building updated workspace..."
if docker ps | grep -q rosmower; then
    echo "Building inside Docker container..."
    docker exec -it rosmower_robot bash -c "cd /workspace && colcon build --packages-select rosmower stereo_camera_viewer --symlink-install"
else
    echo "Docker container not running. Starting..."
    ./docker-helper.sh run -d
    sleep 5
    docker exec -it rosmower_robot bash -c "cd /workspace && colcon build --packages-select rosmower stereo_camera_viewer --symlink-install"
fi

echo ""
echo "[3/5] Launching robot with upgraded sensors..."
./docker-helper.sh launch -d

echo ""
echo "Waiting for nodes to start..."
sleep 10

echo ""
echo "[4/5] Verifying ROS2 topics..."
docker exec -it rosmower_robot bash -c "
source /workspace/install/setup.bash
echo 'Active nodes:'
ros2 node list

echo ''
echo 'LIDAR topics:'
ros2 topic list | grep scan

echo ''
echo 'Camera topics:'
ros2 topic list | grep stereo
"

echo ""
echo "[5/5] Running comprehensive test..."
./test_sensors_upgraded.sh

echo ""
echo "================================================"
echo "  Setup Complete!"
echo "================================================"
echo ""
echo "Your upgraded sensors are now active!"
echo ""
echo "ROS2 Topics:"
echo "  LIDAR:"
echo "    /scan - LaserScan @ ~8-10 Hz"
echo ""
echo "  Stereo Cameras:"
echo "    /stereo/left/image_raw - Left camera @ 30 FPS"
echo "    /stereo/right/image_raw - Right camera @ 30 FPS"
echo "    /stereo/left/image_raw/compressed - Compressed left"
echo "    /stereo/right/image_raw/compressed - Compressed right"
echo ""
echo "Next Steps:"
echo "  1. Visualize in RViz: ./docker-helper.sh rviz"
echo "  2. View camera streams: http://localhost:8080"
echo "  3. Calibrate stereo cameras (see UPGRADED_SENSORS.md)"
echo "  4. Test navigation with new LIDAR range (8m)"
echo ""
echo "Documentation: UPGRADED_SENSORS.md"
echo "================================================"
