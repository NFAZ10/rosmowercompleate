#!/bin/bash
# Verification script for Multi-Zone Route Management System
# This script verifies all components are properly installed

set -e

echo "========================================="
echo "Multi-Zone System Verification"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

PASS="${GREEN}✓${NC}"
FAIL="${RED}✗${NC}"
WARN="${YELLOW}⚠${NC}"

total_checks=0
passed_checks=0

check() {
    total_checks=$((total_checks + 1))
    if eval "$2" > /dev/null 2>&1; then
        echo -e "${PASS} $1"
        passed_checks=$((passed_checks + 1))
        return 0
    else
        echo -e "${FAIL} $1"
        return 1
    fi
}

echo "Checking Message Types..."
check "Route.msg exists" "test -f src/rosmower_msgs/msg/Route.msg"
check "RouteArray.msg exists" "test -f src/rosmower_msgs/msg/RouteArray.msg"
check "ZoneGraph.msg exists" "test -f src/rosmower_msgs/msg/ZoneGraph.msg"
check "ZoneGraphNode.msg exists" "test -f src/rosmower_msgs/msg/ZoneGraphNode.msg"
check "ZoneGraphEdge.msg exists" "test -f src/rosmower_msgs/msg/ZoneGraphEdge.msg"
check "RouteRecordingStatus.msg exists" "test -f src/rosmower_msgs/msg/RouteRecordingStatus.msg"
echo ""

echo "Checking ROS2 Nodes..."
check "route_manager.py exists" "test -f src/rosmower/scripts/route_manager.py"
check "route_planner.py exists" "test -f src/rosmower/scripts/route_planner.py"
check "route_manager.py is executable" "test -x src/rosmower/scripts/route_manager.py"
check "route_planner.py is executable" "test -x src/rosmower/scripts/route_planner.py"
echo ""

echo "Checking Web Interface..."
check "zone_routes.html exists" "test -f src/rosmower/web/zone_routes.html"
check "web_server.py has route APIs" "grep -q 'api/routes' web_server.py"
echo ""

echo "Checking Launch Files..."
check "zone_and_route_management.launch.py exists" "test -f src/rosmower/launch/zone_and_route_management.launch.py"
echo ""

echo "Checking Scripts..."
check "setup_multi_zone_storage.sh exists" "test -f setup_multi_zone_storage.sh"
check "build-multi-zone.sh exists" "test -f build-multi-zone.sh"
check "test_multi_zone_routes.sh exists" "test -f test_multi_zone_routes.sh"
check "All scripts are executable" "test -x setup_multi_zone_storage.sh -a -x build-multi-zone.sh -a -x test_multi_zone_routes.sh"
echo ""

echo "Checking Storage Directories..."
check "routes/ directory exists" "test -d routes"
check "zones/ directory exists" "test -d zones"
check "routes/README.md exists" "test -f routes/README.md"
echo ""

echo "Checking Documentation..."
check "00-MULTI-ZONE-START-HERE.md exists" "test -f 00-MULTI-ZONE-START-HERE.md"
check "MULTI_ZONE_GUIDE.md exists" "test -f MULTI_ZONE_GUIDE.md"
check "ROUTE_RECORDING_GUIDE.md exists" "test -f ROUTE_RECORDING_GUIDE.md"
check "ROUTE_BEST_PRACTICES.md exists" "test -f ROUTE_BEST_PRACTICES.md"
check "ZONE_GRAPH_EXPLAINED.md exists" "test -f ZONE_GRAPH_EXPLAINED.md"
check "MULTI_ZONE_DEPLOYMENT.md exists" "test -f MULTI_ZONE_DEPLOYMENT.md"
check "IMPLEMENTATION_COMPLETE.md exists" "test -f IMPLEMENTATION_COMPLETE.md"
echo ""

echo "Checking Code Quality..."
check "route_manager.py has proper shebang" "head -1 src/rosmower/scripts/route_manager.py | grep -q '#!/usr/bin/env python3'"
check "route_planner.py has proper shebang" "head -1 src/rosmower/scripts/route_planner.py | grep -q '#!/usr/bin/env python3'"
check "route_manager.py has docstrings" "grep -q '\"\"\"' src/rosmower/scripts/route_manager.py"
check "route_planner.py has docstrings" "grep -q '\"\"\"' src/rosmower/scripts/route_planner.py"
echo ""

echo "Checking File Sizes (sanity check)..."
check "route_manager.py has content (>100 lines)" "test $(wc -l < src/rosmower/scripts/route_manager.py) -gt 100"
check "route_planner.py has content (>100 lines)" "test $(wc -l < src/rosmower/scripts/route_planner.py) -gt 100"
check "zone_routes.html has content (>100 lines)" "test $(wc -l < src/rosmower/web/zone_routes.html) -gt 100"
echo ""

echo "========================================="
echo "Verification Results"
echo "========================================="
echo -e "Passed: ${GREEN}${passed_checks}${NC}/${total_checks}"

if [ $passed_checks -eq $total_checks ]; then
    echo -e "${GREEN}✓ ALL CHECKS PASSED${NC}"
    echo ""
    echo "Your Multi-Zone Route Management System is properly installed!"
    echo ""
    echo "Next steps:"
    echo "  1. Build packages: ./build-multi-zone.sh"
    echo "  2. Read quick start: cat 00-MULTI-ZONE-START-HERE.md"
    echo "  3. Deploy system: See MULTI_ZONE_DEPLOYMENT.md"
    exit 0
else
    echo -e "${RED}✗ SOME CHECKS FAILED${NC}"
    echo ""
    echo "Please review the failures above and fix any issues."
    exit 1
fi
