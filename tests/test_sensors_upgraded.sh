#!/bin/bash

# Test script for upgraded sensors: RPlidar C1 and Stereo CSI Cameras
# Verifies hardware detection and ROS2 topic publishing

set -e

CONTAINER="rosmower_robot"
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=========================================="
echo "  Upgraded Sensor Test Suite"
echo "  - RPlidar C1 (460800 baud)"
echo "  - Stereo CSI Cameras (IMX219)"
echo "=========================================="
echo ""

# Function to check if container is running
check_container() {
    if ! docker ps | grep -q "$CONTAINER"; then
        echo -e "${RED}[ERROR]${NC} Docker container '$CONTAINER' is not running!"
        echo "Start it with: ./docker-helper.sh run -d"
        exit 1
    fi
    echo -e "${GREEN}[OK]${NC} Docker container is running"
}

# Function to check hardware device
check_device() {
    local device=$1
    local name=$2
    
    if [ -e "$device" ]; then
        echo -e "${GREEN}[OK]${NC} $name detected at $device"
        ls -l "$device"
        return 0
    else
        echo -e "${RED}[FAIL]${NC} $name NOT found at $device"
        return 1
    fi
}

# Function to check ROS2 topic
check_topic() {
    local topic=$1
    local name=$2
    local timeout=${3:-5}
    
    echo -n "Checking ROS2 topic: $topic ... "
    
    if docker exec -it $CONTAINER timeout $timeout ros2 topic echo "$topic" --once >/dev/null 2>&1; then
        echo -e "${GREEN}[PUBLISHING]${NC}"
        # Show topic info
        docker exec -it $CONTAINER ros2 topic info "$topic" 2>/dev/null | grep -E "Publisher count|Subscription count"
        return 0
    else
        echo -e "${RED}[NOT PUBLISHING]${NC}"
        return 1
    fi
}

echo "=========================================="
echo "1. Hardware Device Detection"
echo "=========================================="

# Check RPlidar C1
echo -e "\n${YELLOW}RPlidar C1:${NC}"
if ls /dev/ttyUSB* >/dev/null 2>&1; then
    for device in /dev/ttyUSB*; do
        check_device "$device" "LIDAR (USB Serial)"
    done
else
    echo -e "${RED}[FAIL]${NC} No USB serial devices found!"
fi

# Check by-id for RPlidar
if ls /dev/serial/by-id/*CP2102* >/dev/null 2>&1; then
    check_device "/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0" "RPlidar C1 (by-id)"
fi

# Check CSI Cameras
echo -e "\n${YELLOW}Stereo CSI Cameras (IMX219):${NC}"
check_device "/dev/video1" "Left Camera (IMX219 @ CAM1)"
check_device "/dev/video2" "Right Camera (IMX219 @ CAM0)"

# Show detailed camera info
echo -e "\n${YELLOW}Camera Details:${NC}"
if command -v v4l2-ctl >/dev/null 2>&1; then
    v4l2-ctl --list-devices 2>/dev/null | grep -A 2 "imx219"
else
    echo "v4l2-ctl not available (install v4l-utils for detailed info)"
fi

echo ""
echo "=========================================="
echo "2. ROS2 Container Status"
echo "=========================================="
check_container

echo ""
echo "=========================================="
echo "3. ROS2 Node Status"
echo "=========================================="

echo -e "\n${YELLOW}Active ROS2 Nodes:${NC}"
docker exec -it $CONTAINER ros2 node list 2>/dev/null || echo "No nodes running"

echo ""
echo "=========================================="
echo "4. ROS2 Topic Tests"
echo "=========================================="

# Test RPlidar C1 topics
echo -e "\n${YELLOW}RPlidar C1 Topics:${NC}"
check_topic "/scan" "LIDAR Scan Data" 10

# Test Stereo Camera topics
echo -e "\n${YELLOW}Stereo Camera Topics:${NC}"
check_topic "/stereo/left/image_raw" "Left Camera Raw Image" 10
check_topic "/stereo/right/image_raw" "Right Camera Raw Image" 10
check_topic "/stereo/left/image_raw/compressed" "Left Camera Compressed" 10
check_topic "/stereo/right/image_raw/compressed" "Right Camera Compressed" 10
check_topic "/stereo/left/camera_info" "Left Camera Info" 5
check_topic "/stereo/right/camera_info" "Right Camera Info" 5

echo ""
echo "=========================================="
echo "5. Topic Publishing Rates"
echo "=========================================="

# Check LIDAR rate (should be ~5-10 Hz for C1)
echo -e "\n${YELLOW}RPlidar C1 Scan Rate:${NC}"
docker exec -it $CONTAINER timeout 10 ros2 topic hz /scan 2>/dev/null || echo "No data"

# Check camera rates (should be ~30 Hz)
echo -e "\n${YELLOW}Left Camera Rate:${NC}"
docker exec -it $CONTAINER timeout 10 ros2 topic hz /stereo/left/image_raw 2>/dev/null || echo "No data"

echo -e "\n${YELLOW}Right Camera Rate:${NC}"
docker exec -it $CONTAINER timeout 10 ros2 topic hz /stereo/right/image_raw 2>/dev/null || echo "No data"

echo ""
echo "=========================================="
echo "6. TF Tree Status"
echo "=========================================="

echo -e "\n${YELLOW}Active TF Frames:${NC}"
docker exec -it $CONTAINER ros2 run tf2_tools view_frames 2>/dev/null || echo "TF tools not available"

echo -e "\n${YELLOW}Camera Frames:${NC}"
docker exec -it $CONTAINER timeout 5 ros2 topic echo /tf_static --once 2>/dev/null | grep -E "stereo_camera|laser_frame" || echo "No camera/LIDAR frames in TF"

echo ""
echo "=========================================="
echo "  Test Summary"
echo "=========================================="
echo ""
echo "Expected ROS2 Topics:"
echo "  LIDAR:"
echo "    - /scan (sensor_msgs/LaserScan) @ ~5-10 Hz"
echo ""
echo "  Stereo Cameras:"
echo "    - /stereo/left/image_raw (sensor_msgs/Image) @ 30 Hz"
echo "    - /stereo/right/image_raw (sensor_msgs/Image) @ 30 Hz"
echo "    - /stereo/left/image_raw/compressed (sensor_msgs/CompressedImage)"
echo "    - /stereo/right/image_raw/compressed (sensor_msgs/CompressedImage)"
echo "    - /stereo/left/camera_info (sensor_msgs/CameraInfo)"
echo "    - /stereo/right/camera_info (sensor_msgs/CameraInfo)"
echo ""
echo "Expected TF Frames:"
echo "    - base_link -> laser_frame (LIDAR)"
echo "    - base_link -> stereo_camera_left"
echo "    - base_link -> stereo_camera_right"
echo ""
echo "=========================================="
echo ""

echo -e "${GREEN}Test complete!${NC}"
echo ""
echo "To visualize in RViz:"
echo "  ./docker-helper.sh rviz"
echo "  Then add:"
echo "    - LaserScan display for /scan"
echo "    - Image display for /stereo/left/image_raw"
echo "    - Image display for /stereo/right/image_raw"
echo ""
