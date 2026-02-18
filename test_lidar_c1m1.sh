#!/bin/bash
# SLAMTEC C1M1 LiDAR Troubleshooting Script

set -e

echo "=== SLAMTEC C1M1 LiDAR Diagnostics ==="
echo ""

# 1. Disable USB autosuspend for all USB devices
echo "[1/6] Disabling USB autosuspend..."
for device in /sys/bus/usb/devices/*/power/control; do
    if [ -f "$device" ]; then
        echo "on" | sudo tee "$device" > /dev/null
    fi
done
echo "✓ USB autosuspend disabled"

# 2. Check device exists
echo ""
echo "[2/6] Checking /dev/rplidar -> /dev/ttyUSB0..."
if [ -L /dev/rplidar ]; then
    echo "✓ /dev/rplidar exists: $(readlink -f /dev/rplidar)"
    ls -la /dev/rplidar
else
    echo "✗ /dev/rplidar not found!"
    exit 1
fi

# 3. Fix permissions
echo ""
echo "[3/6] Setting device permissions..."
sudo chmod 666 /dev/ttyUSB0
echo "✓ Permissions set to 666"

# 4. Check for USB errors in kernel log
echo ""
echo "[4/6] Checking kernel logs for USB errors (last 50 lines)..."
sudo dmesg | grep -i -E "usb|ttyUSB0|ftdi|disconnect" | tail -50 || echo "No USB errors found"

# 5. Launch LiDAR with correct baud rate (400000 for C1M1)
echo ""
echo "[5/6] Launching SLAMTEC C1M1 with correct settings..."
echo "  - Serial port: /dev/rplidar"
echo "  - Baud rate: 400000 (C1M1 specific)"
echo "  - Scan mode: Standard"
echo ""

# Run in Docker container if available, otherwise native
if docker ps | grep -q rosmower_bridge; then
    echo "Using Docker container: rosmower_bridge"
    docker exec -d rosmower_bridge bash -c "
        source /opt/ros/humble/setup.bash && \
        source /ros_ws/install/setup.bash && \
        ros2 launch sllidar_ros2 sllidar_c1_launch.py \
            serial_port:=/dev/rplidar \
            serial_baudrate:=400000 \
            scan_mode:=Standard
    "
    sleep 3
    echo "✓ LiDAR node launched in Docker"
else
    echo "No Docker container running. Launch manually with:"
    echo "  ros2 launch sllidar_ros2 sllidar_c1_launch.py serial_port:=/dev/rplidar serial_baudrate:=400000"
fi

echo ""
echo "[6/6] Monitoring scan topic for 30 seconds..."
echo "Press Ctrl+C to stop monitoring"
echo ""

# Monitor the scan topic
if docker ps | grep -q rosmower_bridge; then
    timeout 30 docker exec rosmower_bridge bash -c "
        source /opt/ros/humble/setup.bash && \
        source /ros_ws/install/setup.bash && \
        ros2 topic hz /scan
    " || echo "Monitoring stopped"
else
    echo "Run: ros2 topic hz /scan"
fi

echo ""
echo "=== Diagnostics Complete ==="
echo ""
echo "Next steps:"
echo "1. Check 'ros2 topic list' to verify /scan exists"
echo "2. Monitor with 'ros2 topic echo /scan --no-arr'"
echo "3. Check node status: 'ros2 node info /sllidar_node'"
echo "4. If issues persist, check:"
echo "   - USB cable quality (try different cable)"
echo "   - USB port power (try different USB port)"
echo "   - USB hub power (if using hub, try direct connection)"
