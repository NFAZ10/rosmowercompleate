#!/bin/bash
# Install systemd service to disable USB autosuspend at boot
# This makes the fix permanent across reboots

set -e

echo "========================================="
echo "Installing USB Autosuspend Service"
echo "========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: This script must be run as root (use sudo)"
    exit 1
fi

echo "[1/3] Creating startup script..."
cat > /usr/local/bin/disable-usb-autosuspend.sh << 'EOF'
#!/bin/bash
# Disable USB autosuspend for robot hardware
# Prevents LIDAR and other USB devices from being suspended

echo -1 > /sys/module/usbcore/parameters/autosuspend

# Also disable for specific device if present
if [ -d /sys/bus/usb/devices/1-2.3 ]; then
    echo 'on' > /sys/bus/usb/devices/1-2.3/power/control
    echo -1 > /sys/bus/usb/devices/1-2.3/power/autosuspend
fi

logger "USB autosuspend disabled for robot hardware"
EOF

chmod +x /usr/local/bin/disable-usb-autosuspend.sh
echo "       Created: /usr/local/bin/disable-usb-autosuspend.sh"

echo ""
echo "[2/3] Creating systemd service..."
cat > /etc/systemd/system/disable-usb-autosuspend.service << 'EOF'
[Unit]
Description=Disable USB Autosuspend for Robot Hardware
Documentation=https://github.com/rosmower
After=multi-user.target
Before=docker.service

[Service]
Type=oneshot
ExecStart=/usr/local/bin/disable-usb-autosuspend.sh
RemainAfterExit=yes
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
echo "       Created: /etc/systemd/system/disable-usb-autosuspend.service"

echo ""
echo "[3/3] Enabling and starting service..."
systemctl daemon-reload
systemctl enable disable-usb-autosuspend.service
systemctl start disable-usb-autosuspend.service

echo ""
echo "========================================="
echo "✅ SERVICE INSTALLED SUCCESSFULLY"
echo "========================================="
echo ""
echo "Service status:"
systemctl status disable-usb-autosuspend.service --no-pager -l || true
echo ""
echo "The service will now run automatically at every boot."
echo "USB autosuspend will be disabled before Docker starts."
echo ""
