#!/bin/bash
# Test if LIDAR autosuspend fix is working

echo "========================================="
echo "LIDAR Fix Verification Test"
echo "========================================="
echo ""

echo "[System Status]"
echo "  USB autosuspend global: $(cat /sys/module/usbcore/parameters/autosuspend)"
if [ -d /sys/bus/usb/devices/1-2.3 ]; then
    echo "  LIDAR power control:    $(cat /sys/bus/usb/devices/1-2.3/power/control)"
    echo "  LIDAR autosuspend:      $(cat /sys/bus/usb/devices/1-2.3/power/autosuspend)"
else
    echo "  LIDAR device:           NOT FOUND (may need to reconnect)"
fi

echo ""
echo "[USB Device Info]"
lsusb | grep -i "cp210\|silicon" || echo "  LIDAR not detected by lsusb"

echo ""
echo "[Device File]"
ls -lah /dev/ttyUSB* 2>/dev/null || echo "  No ttyUSB devices found"

echo ""
echo "[Recent USB Events]"
echo "  Last 10 USB messages from kernel:"
dmesg | grep -i "ttyUSB0\|cp210\|1-2.3" | tail -10

echo ""
echo "[Container Status]"
docker ps --filter "name=rosmower_robot" --format "{{.Names}}\t{{.Status}}" 2>/dev/null || echo "  Container not running"

echo ""
echo "[ROS LIDAR Test]"
if docker ps --filter "name=rosmower_robot" --format "{{.Names}}" | grep -q rosmower_robot; then
    echo "  Testing /scan topic (5 second timeout)..."
    docker exec rosmower_robot bash -c 'source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && timeout 5 ros2 topic hz /scan --window 10' 2>&1 || echo "  ⚠️  No scan data received"
else
    echo "  Container not running - start it with: docker start rosmower_robot"
fi

echo ""
echo "========================================="
echo "Test complete. If you see scan data above,"
echo "the LIDAR is working correctly!"
echo ""
echo "To monitor for disconnects over time, run:"
echo "  watch -n 2 'dmesg | tail -15'"
echo ""
echo "You should see NO new disconnect messages."
echo "========================================="
