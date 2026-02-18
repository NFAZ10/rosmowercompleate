#!/bin/bash
# Phase A Verification Script
# Checks that all components are properly implemented

echo "═══════════════════════════════════════════════════════════════════════════"
echo "   PHASE A VERIFICATION"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""

PASS=0
FAIL=0

# Helper functions
check() {
    if [ $? -eq 0 ]; then
        echo "  ✅ $1"
        ((PASS++))
    else
        echo "  ❌ $1"
        ((FAIL++))
    fi
}

# 1. Check rosmower_msgs package files
echo "1. Checking rosmower_msgs package..."
test -f src/rosmower_msgs/msg/Zone.msg
check "Zone.msg exists"

test -f src/rosmower_msgs/msg/ZoneArray.msg
check "ZoneArray.msg exists"

test -f src/rosmower_msgs/msg/BatteryStatus.msg
check "BatteryStatus.msg exists"

test -f src/rosmower_msgs/msg/Mission.msg
check "Mission.msg exists"

test -f src/rosmower_msgs/srv/SaveZone.srv
check "SaveZone.srv exists"

test -f src/rosmower_msgs/srv/LoadZone.srv
check "LoadZone.srv exists"

test -f src/rosmower_msgs/srv/ListZones.srv
check "ListZones.srv exists"

test -f src/rosmower_msgs/srv/DeleteZone.srv
check "DeleteZone.srv exists"

# 2. Check rosmower package files
echo ""
echo "2. Checking rosmower package..."
test -f src/rosmower/scripts/battery_monitor.py
check "battery_monitor.py exists"

test -x src/rosmower/scripts/battery_monitor.py
check "battery_monitor.py is executable"

test -f src/rosmower/scripts/zone_manager.py
check "zone_manager.py exists"

test -x src/rosmower/scripts/zone_manager.py
check "zone_manager.py is executable"

# 3. Check launch files
echo ""
echo "3. Checking launch files..."
test -f src/rosmower/launch/autonomous_mission.launch.py
check "autonomous_mission.launch.py exists"

# 4. Check config files
echo ""
echo "4. Checking configuration..."
test -f src/rosmower/config/autonomous_mission.yaml
check "autonomous_mission.yaml exists"

# 5. Check web files
echo ""
echo "5. Checking web interface..."
test -f src/rosmower/web/zone_manager.html
check "zone_manager.html exists"

grep -q "zones" src/rosmower/web/mode_control.html
check "mode_control.html updated with zones link"

# 6. Check web server
echo ""
echo "6. Checking web server API..."
grep -q "/api/zones" web_server.py
check "Zone API endpoints in web_server.py"

grep -q "/zones" web_server.py
check "Zone manager route in web_server.py"

# 7. Check zones directory
echo ""
echo "7. Checking zones directory..."
test -d zones
check "zones/ directory exists"

test -f zones/front_yard.yaml
check "front_yard.yaml sample zone exists"

test -f zones/back_yard.yaml
check "back_yard.yaml sample zone exists"

# 8. Check build artifacts
echo ""
echo "8. Checking build artifacts..."
test -d build/rosmower_msgs
check "rosmower_msgs built"

test -d install/rosmower_msgs
check "rosmower_msgs installed"

test -d build/rosmower
check "rosmower built"

test -d install/rosmower
check "rosmower installed"

# 9. Check scripts
echo ""
echo "9. Checking build scripts..."
test -f build-phase-a.sh
check "build-phase-a.sh exists"

test -x build-phase-a.sh
check "build-phase-a.sh is executable"

# 10. Check documentation
echo ""
echo "10. Checking documentation..."
test -f PHASE_A_COMPLETE.md
check "PHASE_A_COMPLETE.md exists"

test -f PHASE_A_SUMMARY.txt
check "PHASE_A_SUMMARY.txt exists"

# Summary
echo ""
echo "═══════════════════════════════════════════════════════════════════════════"
echo "   VERIFICATION RESULTS"
echo "═══════════════════════════════════════════════════════════════════════════"
echo ""
echo "  Passed: $PASS"
echo "  Failed: $FAIL"
echo ""

if [ $FAIL -eq 0 ]; then
    echo "  ✅ ALL CHECKS PASSED - PHASE A COMPLETE!"
    echo ""
    echo "  Next steps:"
    echo "    1. Build packages:    ./build-phase-a.sh"
    echo "    2. Start web server:  ./start-web-server.sh"
    echo "    3. Launch nodes:      ./docker-helper.sh exec ros2 launch rosmower autonomous_mission.launch.py"
    echo "    4. Open web UI:       http://localhost:8080/zones"
    echo ""
    exit 0
else
    echo "  ⚠️  SOME CHECKS FAILED - Review errors above"
    echo ""
    exit 1
fi
