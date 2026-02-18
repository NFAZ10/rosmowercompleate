#!/bin/bash
# Build script for Zone Recording System
# Builds messages and zone recorder node

set -e

echo "=========================================="
echo "Building Zone Recording System"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if we're in the workspace root
if [ ! -f "src/rosmower_msgs/CMakeLists.txt" ]; then
    echo -e "${RED}Error: Must run from workspace root${NC}"
    echo "cd to /mnt/nova_ssd/rosmowercompleate"
    exit 1
fi

# Install Python dependencies
echo -e "${YELLOW}Installing Python dependencies...${NC}"
pip3 install -q pyproj numpy 2>/dev/null || {
    echo -e "${YELLOW}Warning: Could not install pyproj via pip${NC}"
    echo "You may need to install manually: pip3 install pyproj numpy"
}

# Build rosmower_msgs first
echo -e "${YELLOW}Building rosmower_msgs package...${NC}"
colcon build --packages-select rosmower_msgs --cmake-args -DCMAKE_BUILD_TYPE=Release
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ rosmower_msgs built successfully${NC}"
else
    echo -e "${RED}✗ Failed to build rosmower_msgs${NC}"
    exit 1
fi

# Source the install
echo -e "${YELLOW}Sourcing workspace...${NC}"
source install/setup.bash

# Build rosmower package
echo -e "${YELLOW}Building rosmower package...${NC}"
colcon build --packages-select rosmower --cmake-args -DCMAKE_BUILD_TYPE=Release
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ rosmower built successfully${NC}"
else
    echo -e "${RED}✗ Failed to build rosmower${NC}"
    exit 1
fi

# Source again
source install/setup.bash

echo ""
echo "=========================================="
echo -e "${GREEN}Build Complete!${NC}"
echo "=========================================="
echo ""
echo "Verify installation:"
echo "  ros2 interface list | grep ZoneRecording"
echo "  ros2 pkg executables rosmower | grep zone_recorder"
echo ""
echo "Launch zone recorder:"
echo "  ros2 launch rosmower zone_recorder.launch.py"
echo ""
echo "Access web UI:"
echo "  http://localhost:8080/zones/recorder"
echo ""
echo "Run tests:"
echo "  ./test_zone_recording.sh"
echo ""
echo "=========================================="

# Quick verification
echo "Quick verification..."
if ros2 interface list 2>/dev/null | grep -q "ZoneRecordingStatus"; then
    echo -e "${GREEN}✓ Messages found${NC}"
else
    echo -e "${YELLOW}⚠ Messages not found (may need to source install/setup.bash)${NC}"
fi

if [ -f "install/rosmower/lib/rosmower/zone_recorder.py" ]; then
    echo -e "${GREEN}✓ Zone recorder executable installed${NC}"
else
    echo -e "${YELLOW}⚠ Zone recorder executable not found${NC}"
fi

echo ""
echo -e "${GREEN}Ready to record zones!${NC}"
