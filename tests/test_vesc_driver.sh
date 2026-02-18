#!/bin/bash

# VESC Driver Test Script
# Tests VESC connection, motor response, and ROS 2 integration

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "================================================"
echo "  VESC Driver Test Suite"
echo "================================================"
echo ""

# Check if VESC is connected
echo -e "${YELLOW}[1/6] Checking VESC USB connection...${NC}"
if ls /dev/ttyACM* >/dev/null 2>&1; then
    for device in /dev/ttyACM*; do
        echo -e "${GREEN}[OK]${NC} Found VESC at $device"
        ls -l "$device"
    done
else
    echo -e "${RED}[FAIL]${NC} No VESC devices found!"
    echo "Make sure VESC is connected via USB and powered on."
    exit 1
fi

# Check permissions
echo ""
echo -e "${YELLOW}[2/6] Checking permissions...${NC}"
if [ -w /dev/ttyACM0 ]; then
    echo -e "${GREEN}[OK]${NC} Write permission granted"
else
    echo -e "${RED}[WARN]${NC} No write permission. Run:"
    echo "  sudo chmod 666 /dev/ttyACM0"
    echo "  OR"
    echo "  sudo usermod -aG dialout \$USER"
    echo "  (then logout and login)"
fi

# Build the package
echo ""
echo -e "${YELLOW}[3/6] Building vesc_driver package...${NC}"
cd /mnt/nova_ssd/rosmowercompleate
colcon build --packages-select vesc_driver --symlink-install 2>&1 | tail -5
if [ $? -eq 0 ]; then
    echo -e "${GREEN}[OK]${NC} Build successful"
else
    echo -e "${RED}[FAIL]${NC} Build failed"
    exit 1
fi

# Source workspace
source install/setup.bash

# Launch VESC driver (background)
echo ""
echo -e "${YELLOW}[4/6] Launching VESC driver...${NC}"
ros2 launch vesc_driver vesc_driver.launch.py > /tmp/vesc_driver.log 2>&1 &
VESC_PID=$!
sleep 3

# Check if node is running
if ps -p $VESC_PID > /dev/null; then
    echo -e "${GREEN}[OK]${NC} VESC driver node started (PID: $VESC_PID)"
else
    echo -e "${RED}[FAIL]${NC} VESC driver failed to start"
    cat /tmp/vesc_driver.log
    exit 1
fi

# Check topics
echo ""
echo -e "${YELLOW}[5/6] Checking ROS 2 topics...${NC}"
echo "Waiting for topics to appear..."
sleep 2

if ros2 topic list | grep -q "/cmd_vel"; then
    echo -e "${GREEN}[OK]${NC} /cmd_vel topic exists"
else
    echo -e "${RED}[WARN]${NC} /cmd_vel topic not found"
fi

if ros2 topic list | grep -q "joint_states"; then
    echo -e "${GREEN}[OK]${NC} joint_states topic exists"
else
    echo -e "${RED}[WARN]${NC} joint_states topic not found"
fi

# Test motor command
echo ""
echo -e "${YELLOW}[6/6] Testing motor command...${NC}"
echo "Publishing small forward velocity (0.1 m/s) for 2 seconds..."
echo "WARNING: Motors will move! Ensure robot is on blocks or clear area."
read -p "Continue? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    timeout 2 ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
        "{linear: {x: 0.1}, angular: {z: 0.0}}" --once
    echo -e "${GREEN}[OK]${NC} Command sent"
    
    # Stop motors
    sleep 0.5
    ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
        "{linear: {x: 0.0}, angular: {z: 0.0}}" --once
    echo "Motors stopped"
else
    echo "Skipping motor test"
fi

# Show joint states
echo ""
echo "Joint states:"
timeout 3 ros2 topic echo /joint_states --once || echo "No data"

# Cleanup
echo ""
echo -e "${YELLOW}Stopping VESC driver...${NC}"
kill $VESC_PID 2>/dev/null || true
sleep 1

echo ""
echo "================================================"
echo "  Test Summary"
echo "================================================"
echo ""
echo "Next steps:"
echo "  1. Integrate with rosmower launch file:"
echo "     - Add vesc_driver.launch.py to launch_robot.launch.py"
echo "  2. Calibrate wheel radius and separation"
echo "  3. Test with teleop:"
echo "     ros2 run teleop_twist_keyboard teleop_twist_keyboard"
echo "  4. Verify odometry accuracy"
echo ""
echo -e "${GREEN}Test complete!${NC}"
