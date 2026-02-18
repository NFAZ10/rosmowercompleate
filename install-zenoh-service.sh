#!/bin/bash
# Install Zenoh Router as a systemd service using docker-helper.sh
# This ensures Zenoh starts at boot and restarts on failure

set -e

echo "========================================="
echo "Zenoh Router Systemd Service Installer"
echo "========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "ERROR: This script must be run as root (use sudo)"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKER_HELPER="${SCRIPT_DIR}/docker-helper.sh"
ZENOH_CONFIG="${SCRIPT_DIR}/zenoh-router.json5"

echo "[1/5] Verifying required files..."
if [ ! -f "$DOCKER_HELPER" ]; then
    echo "ERROR: docker-helper.sh not found at $DOCKER_HELPER"
    exit 1
fi
if [ ! -f "$ZENOH_CONFIG" ]; then
    echo "ERROR: zenoh-router.json5 not found at $ZENOH_CONFIG"
    exit 1
fi
echo "       ✅ Found: $DOCKER_HELPER"
echo "       ✅ Found: $ZENOH_CONFIG"

echo ""
echo "[2/5] Creating systemd service file..."
cat > /etc/systemd/system/zenoh-router.service << EOF
[Unit]
Description=Zenoh Router for ROS2 Multi-Robot Communication
Documentation=https://zenoh.io/
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=forking
Restart=always
RestartSec=10
StartLimitInterval=0
WorkingDirectory=${SCRIPT_DIR}
User=$(logname 2>/dev/null || echo $SUDO_USER)

# Stop any existing Zenoh containers
ExecStartPre=-/usr/bin/docker stop rosmower_zenoh
ExecStartPre=-/bin/sleep 2

# Start Zenoh router using docker-helper.sh
ExecStart=${DOCKER_HELPER} zenoh -d

# Health check - verify container is running
ExecStartPost=/bin/bash -c 'for i in {1..30}; do if docker ps --filter "name=rosmower_zenoh" --format "{{.Names}}" | grep -q rosmower_zenoh; then exit 0; fi; sleep 1; done; exit 1'

# Stop container on service stop
ExecStop=/usr/bin/docker stop rosmower_zenoh

# Logging
StandardOutput=journal
StandardError=journal
SyslogIdentifier=zenoh-router

[Install]
WantedBy=multi-user.target
EOF

echo "       ✅ Created: /etc/systemd/system/zenoh-router.service"

echo ""
echo "[3/5] Reloading systemd daemon..."
systemctl daemon-reload
echo "       ✅ Systemd reloaded"

echo ""
echo "[4/5] Enabling Zenoh router to start at boot..."
systemctl enable zenoh-router.service
echo "       ✅ Service enabled"

echo ""
echo "[5/5] Checking if old container is running..."
if docker ps --filter "name=rosmower_zenoh" --format "{{.Names}}" | grep -q "rosmower_zenoh"; then
    echo "       Stopping old container..."
    docker stop rosmower_zenoh || true
    sleep 2
fi

echo ""
echo "========================================="
echo "✅ INSTALLATION COMPLETE"
echo "========================================="
echo ""
echo "Zenoh router will now:"
echo "  • Start automatically at boot"
echo "  • Restart automatically if it crashes"
echo "  • Use configuration from: $ZENOH_CONFIG"
echo ""
echo "Control commands:"
echo "  Start:   sudo systemctl start zenoh-router"
echo "  Stop:    sudo systemctl stop zenoh-router"
echo "  Restart: sudo systemctl restart zenoh-router"
echo "  Status:  sudo systemctl status zenoh-router"
echo "  Logs:    sudo journalctl -u zenoh-router -f"
echo ""
echo "To start now:"
echo "  sudo systemctl start zenoh-router"
echo ""
