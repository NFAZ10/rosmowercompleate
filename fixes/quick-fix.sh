#!/bin/bash
# ONE-CLICK LIDAR FIX - Run this with: sudo bash quick-fix.sh

if [ "$EUID" -ne 0 ]; then 
    echo "Please run with: sudo bash quick-fix.sh"
    exit 1
fi

echo "Applying LIDAR USB fix..."

# Stop power daemon
systemctl stop power-profiles-daemon 2>/dev/null
systemctl disable power-profiles-daemon 2>/dev/null

# Disable USB autosuspend
echo -1 > /sys/module/usbcore/parameters/autosuspend

# Disable for LIDAR device
if [ -d /sys/bus/usb/devices/1-2.3 ]; then
    echo 'on' > /sys/bus/usb/devices/1-2.3/power/control
    echo -1 > /sys/bus/usb/devices/1-2.3/power/autosuspend
fi

# Permanent config
cat > /etc/modprobe.d/rosmower-usb.conf << 'EOF'
options usbcore autosuspend=-1
EOF

# Udev rules
cat > /etc/udev/rules.d/99-rosmower-usb-power.rules << 'EOF'
ACTION=="add", SUBSYSTEM=="usb", TEST=="power/control", ATTR{power/control}="on"
ACTION=="add", SUBSYSTEM=="usb", TEST=="power/autosuspend", ATTR{power/autosuspend}="-1"
EOF

udevadm control --reload-rules
udevadm trigger

update-initramfs -u -k all 2>&1 | tail -5

echo "✅ Fix applied!"
echo "USB autosuspend: $(cat /sys/module/usbcore/parameters/autosuspend)"

# Restart container
docker restart rosmower_robot
echo "Container restarting... wait 30 seconds then test with:"
echo "docker exec rosmower_robot bash -c 'source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && ros2 topic hz /scan'"
