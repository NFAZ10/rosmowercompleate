#!/bin/bash
# Installer for WiFi Fallback AP

set -e

echo "Installing WiFi Fallback AP system..."

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Install required packages
echo "Installing required packages..."
apt-get update
apt-get install -y hostapd dnsmasq

# Make script executable
chmod +x "$SCRIPT_DIR/wifi-fallback-ap.sh"

# Install systemd service
echo "Installing systemd service..."
cp "$SCRIPT_DIR/wifi-fallback-ap.service" /etc/systemd/system/
systemctl daemon-reload

# Enable service
echo "Enabling WiFi Fallback AP service..."
systemctl enable wifi-fallback-ap.service

echo ""
echo "Installation complete!"
echo ""
echo "Configuration:"
echo "  AP SSID: RosMower-AP"
echo "  AP Password: rosmower123"
echo "  AP IP: 192.168.50.1"
echo ""
echo "To customize, edit: $SCRIPT_DIR/wifi-fallback-ap.sh"
echo ""
echo "To start now: sudo systemctl start wifi-fallback-ap.service"
echo "To check status: sudo systemctl status wifi-fallback-ap.service"
echo "To view logs: sudo journalctl -u wifi-fallback-ap.service -f"
