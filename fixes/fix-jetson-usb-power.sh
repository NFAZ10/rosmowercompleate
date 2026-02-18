#!/bin/bash
# Jetson-Specific USB Power Management Fix for ROS Mower
# Disables aggressive USB autosuspend that breaks LIDAR in 25W mode

set -e

echo "=============================================="
echo "  JETSON USB POWER MANAGEMENT FIX"
echo "  For ROS Mower LIDAR Stability"
echo "=============================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: This script must be run as root (use sudo)"
    exit 1
fi

# Backup flag
BACKUP_DIR="/root/rosmower-backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
echo "[BACKUP] Creating backup in: $BACKUP_DIR"

# Step 1: Stop and disable power-profiles-daemon
echo ""
echo "[1/6] Stopping power-profiles-daemon..."
if systemctl is-active --quiet power-profiles-daemon; then
    systemctl stop power-profiles-daemon
    echo "       ✓ Stopped power-profiles-daemon"
else
    echo "       ⓘ power-profiles-daemon already stopped"
fi

if systemctl is-enabled --quiet power-profiles-daemon 2>/dev/null; then
    systemctl disable power-profiles-daemon
    echo "       ✓ Disabled power-profiles-daemon (won't start at boot)"
else
    echo "       ⓘ power-profiles-daemon already disabled"
fi

# Step 2: Disable USB autosuspend immediately
echo ""
echo "[2/6] Disabling USB autosuspend globally (immediate)..."
echo -1 > /sys/module/usbcore/parameters/autosuspend
CURRENT=$(cat /sys/module/usbcore/parameters/autosuspend)
echo "       ✓ Global USB autosuspend: $CURRENT (disabled)"

# Step 3: Disable for specific LIDAR device
echo ""
echo "[3/6] Disabling autosuspend for LIDAR device..."
if [ -d /sys/bus/usb/devices/1-2.3 ]; then
    echo 'on' > /sys/bus/usb/devices/1-2.3/power/control
    echo -1 > /sys/bus/usb/devices/1-2.3/power/autosuspend
    echo "       ✓ LIDAR device (1-2.3) power control: on"
else
    echo "       ⚠ LIDAR device (1-2.3) not found - may need to reconnect USB"
fi

# Step 4: Create permanent kernel module configuration
echo ""
echo "[4/6] Creating permanent USB configuration..."

# Backup existing config if present
if [ -f /etc/modprobe.d/rosmower-usb.conf ]; then
    cp /etc/modprobe.d/rosmower-usb.conf "$BACKUP_DIR/"
    echo "       ✓ Backed up existing rosmower-usb.conf"
fi

cat > /etc/modprobe.d/rosmower-usb.conf << 'EOF'
# ROS Mower: Disable USB autosuspend for hardware reliability
# This prevents LIDAR and other USB sensors from disconnecting
# Created by fix-jetson-usb-power.sh

options usbcore autosuspend=-1
EOF
echo "       ✓ Created /etc/modprobe.d/rosmower-usb.conf"

# Step 5: Create udev rules for device-specific control
echo ""
echo "[5/6] Creating udev rules..."

if [ -f /etc/udev/rules.d/99-disable-lidar-autosuspend.rules ]; then
    cp /etc/udev/rules.d/99-disable-lidar-autosuspend.rules "$BACKUP_DIR/"
    echo "       ✓ Backed up existing udev rules"
fi

cat > /etc/udev/rules.d/99-rosmower-usb-power.rules << 'EOF'
# ROS Mower: Disable USB autosuspend for robot hardware
# Prevents power-profiles-daemon from suspending USB devices
# Created by fix-jetson-usb-power.sh

# Disable autosuspend for all USB devices to prevent robot hardware issues
ACTION=="add", SUBSYSTEM=="usb", TEST=="power/control", ATTR{power/control}="on"
ACTION=="add", SUBSYSTEM=="usb", TEST=="power/autosuspend", ATTR{power/autosuspend}="-1"

# Specific rule for RPLiDAR (Silicon Labs CP210x)
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="10c4", ATTR{idProduct}=="ea60", TEST=="power/control", ATTR{power/control}="on"
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="10c4", ATTR{idProduct}=="ea60", TEST=="power/autosuspend", ATTR{power/autosuspend}="-1"

# Hoverboard motor controller (CH340/CH341)
ACTION=="add", SUBSYSTEM=="usb", ATTR{idVendor}=="1a86", TEST=="power/control", ATTR{power/control}="on"
EOF
echo "       ✓ Created /etc/udev/rules.d/99-rosmower-usb-power.rules"

# Reload udev
udevadm control --reload-rules
udevadm trigger
echo "       ✓ Reloaded udev rules"

# Step 6: Update initramfs to include modprobe changes
echo ""
echo "[6/6] Updating initramfs (this may take a minute)..."
if command -v update-initramfs >/dev/null 2>&1; then
    update-initramfs -u -k all > /tmp/initramfs-update.log 2>&1 || {
        echo "       ⚠ initramfs update had warnings (check /tmp/initramfs-update.log)"
    }
    echo "       ✓ Updated initramfs"
else
    echo "       ⓘ update-initramfs not found (changes will apply at next reboot)"
fi

# Verification
echo ""
echo "=============================================="
echo "  ✅ FIX APPLIED SUCCESSFULLY"
echo "=============================================="
echo ""
echo "Current Status:"
echo "  • power-profiles-daemon:  $(systemctl is-active power-profiles-daemon 2>/dev/null || echo 'inactive')"
echo "  • USB autosuspend global: $(cat /sys/module/usbcore/parameters/autosuspend)"
if [ -d /sys/bus/usb/devices/1-2.3 ]; then
    echo "  • LIDAR power control:    $(cat /sys/bus/usb/devices/1-2.3/power/control)"
fi
echo ""
echo "Files Created/Modified:"
echo "  • /etc/modprobe.d/rosmower-usb.conf"
echo "  • /etc/udev/rules.d/99-rosmower-usb-power.rules"
echo "  • Backups saved to: $BACKUP_DIR"
echo ""
echo "=============================================="
echo "  NEXT STEPS"
echo "=============================================="
echo ""
echo "1. Restart ROS container:"
echo "   docker restart rosmower_robot"
echo ""
echo "2. Wait 30 seconds for startup:"
echo "   sleep 30"
echo ""
echo "3. Test LIDAR:"
echo "   docker exec rosmower_robot bash -c 'source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && timeout 5 ros2 topic hz /scan'"
echo ""
echo "4. Monitor for USB disconnects (run for 30+ minutes):"
echo "   watch -n 2 'dmesg | tail -15'"
echo ""
echo "   You should see NO new disconnect messages!"
echo ""
echo "5. Optional: Run test script:"
echo "   cd /mnt/nova_ssd/rosmowercompleate && ./test-lidar-fix.sh"
echo ""
echo "=============================================="
echo ""
echo "Note: These changes are PERMANENT and will persist"
echo "across reboots and power mode changes."
echo ""
echo "To verify at any time: cat /sys/module/usbcore/parameters/autosuspend"
echo "Should always show: -1"
echo ""
