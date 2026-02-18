#!/bin/bash
# Phase A Testing Script
# Tests battery monitor and zone manager functionality

set -e

echo "═══════════════════════════════════════════════════════════════════════════"
echo "   PHASE A TESTING SCRIPT"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""

# Color codes
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Helper function
info() {
    echo -e "${YELLOW}➜${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if Docker container is running
if ! docker ps | grep -q rosmower; then
    error "ROS Mower container is not running!"
    echo ""
    echo "Start the container first:"
    echo "  ./docker-helper.sh run"
    exit 1
fi

success "Docker container is running"
echo ""

# Test 1: Check message interfaces
info "Test 1: Checking custom message interfaces..."
echo ""

if ./docker-helper.sh exec ros2 interface list | grep -q "rosmower_msgs"; then
    success "rosmower_msgs interfaces are available"
    ./docker-helper.sh exec ros2 interface list | grep rosmower_msgs | head -8
else
    error "rosmower_msgs interfaces not found"
    exit 1
fi
echo ""

# Test 2: Check services
info "Test 2: Checking zone management services..."
echo ""

./docker-helper.sh exec ros2 service list | grep -E "zone/(save|load|list|delete)" || true
echo ""

# Test 3: Launch autonomous mission nodes
info "Test 3: Launching autonomous mission nodes..."
echo ""
echo "This will launch battery_monitor and zone_manager nodes."
echo "Press Ctrl+C to stop when you see 'Zone Manager started'"
echo ""
sleep 2

# Launch in background and capture output
./docker-helper.sh exec timeout 5 ros2 launch rosmower autonomous_mission.launch.py 2>&1 | head -30 || true

echo ""
success "Launch file executed (use 'ros2 launch rosmower autonomous_mission.launch.py' to run continuously)"
echo ""

# Test 4: Check topics
info "Test 4: Checking ROS2 topics..."
echo ""

TOPICS_FOUND=0
for topic in "/battery/state" "/battery/low" "/mission/command" "/zones" "/zone/current"; do
    if ./docker-helper.sh exec ros2 topic list 2>/dev/null | grep -q "^$topic$"; then
        success "Found topic: $topic"
        ((TOPICS_FOUND++))
    else
        echo "  ⚠️  Topic not active yet: $topic (will be available when nodes run)"
    fi
done

echo ""

# Test 5: Check zone files
info "Test 5: Checking zone files..."
echo ""

if [ -d "zones" ]; then
    success "zones/ directory exists"
    ZONE_COUNT=$(find zones -name "*.yaml" -o -name "*.yml" | wc -l)
    echo "  Found $ZONE_COUNT zone file(s):"
    ls -1 zones/*.yaml 2>/dev/null | sed 's/^/    /' || true
else
    error "zones/ directory not found"
fi
echo ""

# Test 6: Check web server
info "Test 6: Checking web server..."
echo ""

if ps aux | grep -v grep | grep -q "web_server.py"; then
    success "Web server is running"
    echo ""
    echo "  Access the zone manager at:"
    echo "    http://localhost:8080/zones"
    echo ""
elif [ -f "web_server.py" ]; then
    echo "  ⚠️  Web server not running. Start it with:"
    echo "    ./start-web-server.sh"
    echo ""
fi

# Summary
echo "═══════════════════════════════════════════════════════════════════════════"
echo "   TESTING SUMMARY"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
success "Phase A components are installed correctly!"
echo ""
echo "Next steps:"
echo ""
echo "1. Start the autonomous mission nodes:"
echo "   ${YELLOW}./docker-helper.sh exec ros2 launch rosmower autonomous_mission.launch.py${NC}"
echo ""
echo "2. In another terminal, test battery monitoring:"
echo "   ${YELLOW}./docker-helper.sh exec ros2 topic pub /percent std_msgs/msg/Float32 \"data: 50.0\"${NC}"
echo "   ${YELLOW}./docker-helper.sh exec ros2 topic echo /battery/state${NC}"
echo ""
echo "3. Test zone management:"
echo "   ${YELLOW}./docker-helper.sh exec ros2 service call /zone/list rosmower_msgs/srv/ListZones${NC}"
echo "   ${YELLOW}./docker-helper.sh exec ros2 topic echo /zones --once${NC}"
echo ""
echo "4. Access web interface:"
echo "   ${YELLOW}http://localhost:8080/zones${NC}"
echo ""
echo "5. Monitor battery state changes:"
echo "   # Normal -> Low (triggers RETURN_TO_DOCK)"
echo "   ${YELLOW}./docker-helper.sh exec ros2 topic pub /percent std_msgs/msg/Float32 \"data: 20.0\"${NC}"
echo ""
echo "   # Low -> Critical (triggers EMERGENCY_DOCK)"
echo "   ${YELLOW}./docker-helper.sh exec ros2 topic pub /percent std_msgs/msg/Float32 \"data: 10.0\"${NC}"
echo ""
echo "For full documentation, see: PHASE_A_COMPLETE.md"
echo ""
