#!/bin/bash
# Install ROS Mower Web Server as a systemd service

set -e

echo "Installing ROS Mower Web Server..."

# Install Python dependencies
echo "Installing Python dependencies..."
pip3 install flask flask-cors

# Copy service file to systemd
echo "Installing systemd service..."
sudo cp rosmower-web.service /etc/systemd/system/

# Reload systemd
echo "Reloading systemd..."
sudo systemctl daemon-reload

# Enable and start service
echo "Enabling service..."
sudo systemctl enable rosmower-web.service

echo "Starting service..."
sudo systemctl start rosmower-web.service

# Check status
echo ""
echo "Service status:"
sudo systemctl status rosmower-web.service --no-pager

echo ""
echo "✅ Installation complete!"
echo ""
echo "Access the control panel at:"
echo "  http://localhost:8080"
echo "  http://$(hostname -I | awk '{print $1}'):8080"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status rosmower-web   # Check status"
echo "  sudo systemctl stop rosmower-web     # Stop server"
echo "  sudo systemctl restart rosmower-web  # Restart server"
echo "  sudo journalctl -u rosmower-web -f   # View logs"
