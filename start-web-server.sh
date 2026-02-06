#!/bin/bash
# Quick start script for ROS Mower Web Server (without systemd)

cd /mnt/nova_ssd/rosmowercompleate

echo "========================================"
echo "Starting ROS Mower Web Server"
echo "========================================"
echo ""
echo "Installing dependencies if needed..."
pip3 install -q flask flask-cors 2>/dev/null || true

echo ""
echo "Starting web server on port 8080..."
echo "Access the control panel at:"
echo "  http://localhost:8080"
echo "  http://$(hostname -I | awk '{print $1}'):8080"
echo ""
echo "Press Ctrl+C to stop"
echo "========================================"
echo ""

python3 web_server.py
