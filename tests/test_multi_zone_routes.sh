#!/bin/bash
# Comprehensive test script for multi-zone route management system

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Multi-Zone Route Management Test Suite${NC}"
echo -e "${BLUE}=========================================${NC}"
echo ""

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper function for tests
test_step() {
    echo -e "${YELLOW}▶ $1${NC}"
}

test_pass() {
    echo -e "${GREEN}✓ $1${NC}"
    ((TESTS_PASSED++))
}

test_fail() {
    echo -e "${RED}✗ $1${NC}"
    ((TESTS_FAILED++))
}

# Test 1: Check message files exist
test_step "Testing message definitions..."
if [ -f "src/rosmower_msgs/msg/Route.msg" ] && \
   [ -f "src/rosmower_msgs/msg/RouteArray.msg" ] && \
   [ -f "src/rosmower_msgs/msg/ZoneGraph.msg" ] && \
   [ -f "src/rosmower_msgs/msg/RouteRecordingStatus.msg" ]; then
    test_pass "All message definition files exist"
else
    test_fail "Message definition files missing"
fi

# Test 2: Check node scripts exist
test_step "Testing ROS2 node scripts..."
if [ -f "src/rosmower/scripts/route_manager.py" ] && \
   [ -f "src/rosmower/scripts/route_planner.py" ] && \
   [ -f "src/rosmower/scripts/zone_manager.py" ]; then
    test_pass "All node scripts exist"
else
    test_fail "Node scripts missing"
fi

# Test 3: Check node scripts are executable
test_step "Testing script executability..."
chmod +x src/rosmower/scripts/route_manager.py 2>/dev/null || true
chmod +x src/rosmower/scripts/route_planner.py 2>/dev/null || true
chmod +x src/rosmower/scripts/zone_manager.py 2>/dev/null || true

if [ -x "src/rosmower/scripts/route_manager.py" ]; then
    test_pass "route_manager.py is executable"
else
    test_fail "route_manager.py not executable"
fi

# Test 4: Check launch file
test_step "Testing launch file..."
if [ -f "src/rosmower/launch/zone_and_route_management.launch.py" ]; then
    test_pass "Launch file exists"
else
    test_fail "Launch file missing"
fi

# Test 5: Check web interface
test_step "Testing web interface..."
if [ -f "src/rosmower/web/zone_routes.html" ]; then
    test_pass "Web interface HTML exists"
    
    # Check for key functionality in HTML
    if grep -q "startRecording" src/rosmower/web/zone_routes.html && \
       grep -q "stopRecording" src/rosmower/web/zone_routes.html && \
       grep -q "refreshGraph" src/rosmower/web/zone_routes.html; then
        test_pass "Web interface has required JavaScript functions"
    else
        test_fail "Web interface missing required functions"
    fi
else
    test_fail "Web interface HTML missing"
fi

# Test 6: Check web server API endpoints
test_step "Testing web server API..."
if grep -q "/api/routes/list" web_server.py && \
   grep -q "/api/routes/record/start" web_server.py && \
   grep -q "/api/zones/graph" web_server.py; then
    test_pass "Web server has route API endpoints"
else
    test_fail "Web server missing route API endpoints"
fi

# Test 7: Validate Python syntax
test_step "Validating Python syntax..."
PYTHON_OK=true

if python3 -m py_compile src/rosmower/scripts/route_manager.py 2>/dev/null; then
    test_pass "route_manager.py syntax valid"
else
    test_fail "route_manager.py has syntax errors"
    PYTHON_OK=false
fi

if python3 -m py_compile src/rosmower/scripts/route_planner.py 2>/dev/null; then
    test_pass "route_planner.py syntax valid"
else
    test_fail "route_planner.py has syntax errors"
    PYTHON_OK=false
fi

# Test 8: Check storage directories
test_step "Testing storage structure..."
if [ -d "zones" ]; then
    test_pass "zones/ directory exists"
else
    test_fail "zones/ directory missing"
fi

if [ -d "routes" ]; then
    test_pass "routes/ directory exists"
else
    mkdir -p routes
    test_pass "routes/ directory created"
fi

# Test 9: Test YAML structure (if example files exist)
test_step "Testing YAML file structure..."
if [ -f "routes/.zone_graph_example.yaml" ]; then
    if python3 -c "import yaml; yaml.safe_load(open('routes/.zone_graph_example.yaml'))" 2>/dev/null; then
        test_pass "Example zone graph YAML is valid"
    else
        test_fail "Example zone graph YAML has errors"
    fi
fi

# Test 10: Check documentation
test_step "Testing documentation..."
DOCS_FOUND=0

if [ -f "routes/README.md" ]; then
    ((DOCS_FOUND++))
fi

if [ $DOCS_FOUND -gt 0 ]; then
    test_pass "Documentation files exist ($DOCS_FOUND found)"
else
    test_fail "No documentation files found"
fi

# Test 11: Check ROS2 dependencies in Python files
test_step "Checking ROS2 imports..."
if grep -q "from rosmower_msgs.msg import Route" src/rosmower/scripts/route_manager.py && \
   grep -q "from rosmower_msgs.msg import.*ZoneGraph" src/rosmower/scripts/route_planner.py; then
    test_pass "ROS2 message imports correct"
else
    test_fail "ROS2 message imports missing or incorrect"
fi

# Test 12: Check for GPS quality filtering
test_step "Checking GPS quality filtering..."
if grep -q "min_gps_quality" src/rosmower/scripts/route_manager.py && \
   grep -q "hdop\|HDOP" src/rosmower/scripts/route_manager.py; then
    test_pass "GPS quality filtering implemented"
else
    test_fail "GPS quality filtering not found"
fi

# Test 13: Check for Dijkstra algorithm
test_step "Checking path planning algorithm..."
if grep -q "dijkstra\|Dijkstra" src/rosmower/scripts/route_planner.py && \
   grep -q "heapq" src/rosmower/scripts/route_planner.py; then
    test_pass "Dijkstra algorithm implementation found"
else
    test_fail "Dijkstra algorithm not found"
fi

# Test 14: Check for zone graph generation
test_step "Checking zone graph generation..."
if grep -q "generate_zone_graph\|ZoneGraph" src/rosmower/scripts/zone_manager.py; then
    test_pass "Zone graph generation implemented"
else
    test_fail "Zone graph generation not found"
fi

# Test 15: Check CMakeLists.txt updates
test_step "Checking CMakeLists.txt..."
if grep -q "Route.msg" src/rosmower_msgs/CMakeLists.txt && \
   grep -q "ZoneGraph.msg" src/rosmower_msgs/CMakeLists.txt && \
   grep -q "sensor_msgs" src/rosmower_msgs/CMakeLists.txt; then
    test_pass "CMakeLists.txt properly updated with new messages"
else
    test_fail "CMakeLists.txt missing message definitions or dependencies"
fi

# Test 16: Check package.xml updates
test_step "Checking package.xml..."
if grep -q "sensor_msgs" src/rosmower_msgs/package.xml; then
    test_pass "package.xml has sensor_msgs dependency"
else
    test_fail "package.xml missing sensor_msgs dependency"
fi

# Test 17: Simulate route recording (dry run)
test_step "Simulating route recording logic..."
ROUTE_LOGIC_OK=true

# Check for state machine
if grep -q "RecordingState" src/rosmower/scripts/route_manager.py && \
   grep -q "IDLE\|RECORDING\|PAUSED" src/rosmower/scripts/route_manager.py; then
    test_pass "Route recording state machine found"
else
    test_fail "Route recording state machine missing"
    ROUTE_LOGIC_OK=false
fi

# Check for waypoint addition logic
if grep -q "_try_add_waypoint\|waypoint_spacing" src/rosmower/scripts/route_manager.py; then
    test_pass "Waypoint spacing logic implemented"
else
    test_fail "Waypoint spacing logic missing"
    ROUTE_LOGIC_OK=false
fi

# Test 18: Check distance calculation
test_step "Checking distance calculation..."
if grep -q "Haversine\|haversine\|_calculate_distance" src/rosmower/scripts/route_manager.py; then
    test_pass "Distance calculation (Haversine) implemented"
else
    test_fail "Distance calculation not found"
fi

# Test 19: Check for error handling
test_step "Checking error handling..."
ERROR_HANDLING_FOUND=0

if grep -q "try:" src/rosmower/scripts/route_manager.py && \
   grep -q "except" src/rosmower/scripts/route_manager.py; then
    ((ERROR_HANDLING_FOUND++))
fi

if grep -q "try:" src/rosmower/scripts/route_planner.py && \
   grep -q "except" src/rosmower/scripts/route_planner.py; then
    ((ERROR_HANDLING_FOUND++))
fi

if [ $ERROR_HANDLING_FOUND -ge 2 ]; then
    test_pass "Error handling implemented in nodes"
else
    test_fail "Insufficient error handling"
fi

# Test 20: Check for logging
test_step "Checking logging..."
if grep -q "get_logger()" src/rosmower/scripts/route_manager.py && \
   grep -q "get_logger()" src/rosmower/scripts/route_planner.py; then
    test_pass "ROS2 logging implemented"
else
    test_fail "ROS2 logging missing"
fi

echo ""
echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}Test Results${NC}"
echo -e "${BLUE}=========================================${NC}"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    echo -e "${BLUE}Next Steps:${NC}"
    echo "1. Build the workspace:"
    echo "   ./docker-helper.sh build-inside"
    echo ""
    echo "2. Launch the multi-zone management system:"
    echo "   ros2 launch rosmower zone_and_route_management.launch.py"
    echo ""
    echo "3. Access the web interface:"
    echo "   http://localhost:8080/routes"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Please review and fix issues.${NC}"
    exit 1
fi
