#!/bin/bash
# Complete RTK System Startup Script for ROS2 Workspace

PASSWORD="824656789"
WORKSPACE="/mnt/nova_ssd/rosmowercompleate"

echo "=== Starting RTK GPS System ==="

# 1. Stop any existing GPS services
echo "[1/5] Stopping existing GPS services..."
sudo killall gpsd rtkrcv 2>/dev/null
sleep 1

# 2. Configure LC29HDA for UBX (if needed)
# Uncomment this line at final location:
# echo "[2/5] Configuring LC29HDA for UBX..."
# echo $PASSWORD | sudo -S ~/rtk/configure_lc29h_ubx.sh

# 3. Start RTKLIB rtkrcv
echo "[2/5] Starting RTKLIB rtkrcv..."
cd ~/RTKLIB-2.4.3/app/consapp/rtkrcv/gcc
echo $PASSWORD | sudo -S ./rtkrcv -s -o ~/rtk/rover.conf &
sleep 3

# 4. Verify RTKLIB is outputting to port 9001
echo "[3/5] Checking RTKLIB output..."
timeout 2 nc localhost 9001 | head -3

echo "[4/5] Sourcing ROS2 workspace..."
source $WORKSPACE/install/setup.bash

echo "[5/5] RTK system ready!"
echo ""
echo "To launch ROS2 RTK GPS node:"
echo "  ros2 launch gps_rtk rtklib.launch.py"
echo ""
echo "To monitor RTK position:"
echo "  ros2 topic echo /gps/fix"
echo ""
echo "To check RTK solution quality:"
echo "  ros2 topic echo /gps/fix --field status.status"
echo "    0 = No fix, 1 = Float, 2 = RTK Fixed"

