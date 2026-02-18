#!/bin/bash
# Quick test to verify RPlidar A1 is working properly

set -e

echo "========================================="
echo "RPlidar A1 Quick Test"
echo "========================================="
echo ""

# Find the active dev container
CONTAINER=$(docker ps --filter "name=rosmower_dev" --format "{{.Names}}" | head -1)

if [ -z "$CONTAINER" ]; then
    echo "❌ No rosmower_dev container running!"
    echo "   Start with: ./docker-helper.sh dev -d"
    exit 1
fi

echo "✅ Using container: $CONTAINER"
echo ""

# Test 1: Check if LiDAR node is running
echo "[Test 1] Checking for /rplidar node..."
if docker exec $CONTAINER bash -c "source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && ros2 node list" | grep -q "/rplidar"; then
    echo "         ✅ LiDAR node is running"
else
    echo "         ⚠️  LiDAR node NOT running"
    echo "         Starting LiDAR: ros2 launch rosmower rplidar.launch.py &"
    docker exec -d $CONTAINER bash -c "source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && ros2 launch rosmower rplidar.launch.py"
    echo "         Waiting 5 seconds for startup..."
    sleep 5
fi

echo ""

# Test 2: Check if /scan topic exists
echo "[Test 2] Checking /scan topic..."
if docker exec $CONTAINER bash -c "source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && ros2 topic list" | grep -q "^/scan$"; then
    echo "         ✅ /scan topic exists"
else
    echo "         ❌ /scan topic not found!"
    exit 1
fi

echo ""

# Test 3: Check scan data rate
echo "[Test 3] Measuring scan rate (10 seconds)..."
echo "         Expected: 5-8 Hz for RPlidar A1"
docker exec $CONTAINER bash -c "source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && timeout 10 ros2 topic hz /scan --window 10" || echo "         (Completed)"

echo ""

# Test 4: Get one scan sample
echo "[Test 4] Getting scan sample..."
SCAN_DATA=$(docker exec $CONTAINER bash -c "source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && timeout 3 ros2 topic echo /scan --once" 2>&1 || true)

if echo "$SCAN_DATA" | grep -q "ranges:"; then
    NUM_RANGES=$(echo "$SCAN_DATA" | grep -o "ranges:" | wc -l)
    echo "         ✅ Received laser scan data"
    echo "         Data includes range measurements"
else
    echo "         ⚠️  No scan data received in 3 seconds"
    echo "         Motor might not be spinning. Try:"
    echo "         ros2 service call /start_motor std_srvs/srv/Empty"
fi

echo ""

# Test 5: Check hardware health
echo "[Test 5] Hardware status..."
echo "         USB Device:"
lsusb | grep -i "silicon\|cp210" || echo "         ⚠️  LiDAR not detected by lsusb"
echo "         Device file:"
ls -lah /dev/ttyUSB0 2>/dev/null || echo "         ⚠️  /dev/ttyUSB0 not found"
echo "         USB Power:"
cat /sys/module/usbcore/parameters/autosuspend || echo "         (unable to check)"
if [ -d /sys/bus/usb/devices/1-2.3 ]; then
    echo "         LiDAR power control: $(cat /sys/bus/usb/devices/1-2.3/power/control)"
fi

echo ""
echo "========================================="
echo "✅ Test Complete!"
echo "========================================="
echo ""
echo "If all tests passed, your LiDAR is working correctly."
echo ""
echo "Next steps:"
echo "  • Launch full robot stack: ros2 launch rosmower launch_robot.launch.py"
echo "  • Visualize in RViz: ./docker-helper.sh rviz -d"
echo "  • Start zone recording when GPS is available"
echo ""
