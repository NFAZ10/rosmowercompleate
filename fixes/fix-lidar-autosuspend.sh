#!/bin/bash
# Fix LIDAR USB autosuspend issue
# This script disables USB power management that causes LIDAR disconnects

set -e

echo "========================================="
echo "LIDAR USB Autosuspend Fix Script"
echo "========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: This script must be run as root (use sudo)"
    exit 1
fi

echo "[1/4] Disabling global USB autosuspend..."
echo -1 > /sys/module/usbcore/parameters/autosuspend
CURRENT=$(cat /sys/module/usbcore/parameters/autosuspend)
echo "       Global USB autosuspend: $CURRENT (should be -1)"

echo ""
echo "[2/4] Disabling autosuspend for LIDAR device (1-2.3)..."
if [ -d /sys/bus/usb/devices/1-2.3 ]; then
    echo 'on' > /sys/bus/usb/devices/1-2.3/power/control
    echo -1 > /sys/bus/usb/devices/1-2.3/power/autosuspend
    POWER_CTRL=$(cat /sys/bus/usb/devices/1-2.3/power/control)
    echo "       LIDAR power control: $POWER_CTRL (should be 'on')"
else
    echo "       WARNING: Device 1-2.3 not found. LIDAR may not be connected."
fi

echo ""
echo "[3/4] Creating udev rule for permanent fix..."
cat > /etc/udev/rules.d/99-disable-lidar-autosuspend.rules << 'EOF'
# Disable USB autosuspend for RPLiDAR (Silicon Labs CP210x UART Bridge)
# This prevents the LIDAR from being suspended and disconnecting
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="10c4", ATTR{idProduct}=="ea60", TEST=="power/control", ATTR{power/control}="on"
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="10c4", ATTR{idProduct}=="ea60", TEST=="power/autosuspend", ATTR{power/autosuspend}="-1"
EOF
echo "       Created: /etc/udev/rules.d/99-disable-lidar-autosuspend.rules"

echo ""
echo "[4/4] Reloading udev rules..."
udevadm control --reload-rules
udevadm trigger
echo "       Udev rules reloaded"

echo ""
echo "========================================="
echo "✅ FIX APPLIED SUCCESSFULLY"
echo "========================================="
echo ""
echo "Current USB autosuspend status:"
echo "  Global setting: $(cat /sys/module/usbcore/parameters/autosuspend)"
if [ -d /sys/bus/usb/devices/1-2.3 ]; then
    echo "  LIDAR device:   $(cat /sys/bus/usb/devices/1-2.3/power/control)"
fi
echo ""
echo "Next steps:"
echo "  1. Restart ROS container: docker restart rosmower_robot"
echo "  2. Wait 30 seconds for startup"
echo "  3. Test LIDAR: docker exec rosmower_robot bash -c 'source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && timeout 5 ros2 topic echo /scan --once'"
echo "  4. Monitor for disconnects: watch -n 1 'dmesg | tail -10'"
echo ""
echo "If you still see disconnects after 30 minutes, the issue may be:"
echo "  - Loose USB cable (re-seat cable)"
echo "  - Failing USB hub (try direct connection)"
echo "  - Insufficient power (check 5V supply)"
echo ""
