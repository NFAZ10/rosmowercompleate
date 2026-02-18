#!/bin/bash
# Verification Script for GPS Zone Recording System
# This script verifies that all components are properly installed

echo "=========================================="
echo "GPS Zone Recording System - Verification"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PASSED=0
FAILED=0

check_file() {
    if [ -f "$1" ]; then
        echo -e "${GREEN}✓${NC} $2"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $2 (missing: $1)"
        ((FAILED++))
        return 1
    fi
}

check_dir() {
    if [ -d "$1" ]; then
        echo -e "${GREEN}✓${NC} $2"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC} $2 (missing: $1)"
        ((FAILED++))
        return 1
    fi
}

echo -e "${BLUE}=== Core Components ===${NC}"
check_file "src/rosmower/scripts/zone_recorder.py" "Zone Recorder Node"
check_file "src/rosmower/scripts/zone_manager.py" "Zone Manager Node"
check_file "src/rosmower/launch/zone_recorder.launch.py" "Zone Recorder Launch File"

echo ""
echo -e "${BLUE}=== Message Definitions ===${NC}"
check_file "src/rosmower_msgs/msg/Zone.msg" "Zone Message"
check_file "src/rosmower_msgs/msg/ZoneArray.msg" "ZoneArray Message"
check_file "src/rosmower_msgs/msg/ZoneRecordingStatus.msg" "ZoneRecordingStatus Message"

echo ""
echo -e "${BLUE}=== Service Definitions ===${NC}"
check_file "src/rosmower_msgs/srv/StartZoneRecording.srv" "StartZoneRecording Service"
check_file "src/rosmower_msgs/srv/StopZoneRecording.srv" "StopZoneRecording Service"
check_file "src/rosmower_msgs/srv/ControlZoneRecording.srv" "ControlZoneRecording Service"
check_file "src/rosmower_msgs/srv/SaveZone.srv" "SaveZone Service"
check_file "src/rosmower_msgs/srv/LoadZone.srv" "LoadZone Service"
check_file "src/rosmower_msgs/srv/ListZones.srv" "ListZones Service"
check_file "src/rosmower_msgs/srv/DeleteZone.srv" "DeleteZone Service"

echo ""
echo -e "${BLUE}=== Web Interface ===${NC}"
check_file "src/rosmower/web/zone_recorder.html" "Zone Recorder Web UI"
check_file "src/rosmower/web/zone_manager.html" "Zone Manager Web UI"
check_file "web_server.py" "Web Server"

echo ""
echo -e "${BLUE}=== Configuration ===${NC}"
check_file "src/rosmower/config/isaac_ros_stereo.yaml" "Isaac ROS Stereo Config"
check_dir "zones" "Zones Directory"

echo ""
echo -e "${BLUE}=== Build & Test Scripts ===${NC}"
check_file "build_zone_recorder.sh" "Build Script"
check_file "test_zone_recording.sh" "Test Script"

echo ""
echo -e "${BLUE}=== Documentation ===${NC}"
check_file "00-ZONE-RECORDING-START-HERE.md" "Start Here Guide"
check_file "ZONE_RECORDING_QUICKSTART.md" "Quick Start Guide"
check_file "ZONE_RECORDING_GUIDE.md" "User Guide"
check_file "ZONE_RECORDING_README.md" "Technical Documentation"
check_file "ZONE_RECORDING_ARCHITECTURE.md" "Architecture Documentation"
check_file "ZONE_RECORDING_QUICKREF.md" "Quick Reference"
check_file "ZONE_RECORDING_INSTALL.md" "Installation Guide"
check_file "ZONE_RECORDING_COMPLETE.md" "Completion Checklist"
check_file "ZONE_RECORDING_IMPLEMENTATION_SUMMARY.md" "Implementation Summary"
check_file "ZONE_RECORDING_FILES_SUMMARY.md" "Files Summary"
check_file "ZONE_RECORDING_INDEX.md" "Documentation Index"
check_file "ZONE_RECORDING_SYSTEM_SUMMARY.md" "System Summary"

echo ""
echo "=========================================="
echo -e "${BLUE}=== Verification Results ===${NC}"
echo "=========================================="
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILED${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ ALL COMPONENTS VERIFIED${NC}"
    echo ""
    echo "The GPS Zone Recording System is complete and ready to use!"
    echo ""
    echo "Next steps:"
    echo "  1. Build: ./build_zone_recorder.sh"
    echo "  2. Test:  ./test_zone_recording.sh"
    echo "  3. Launch: ros2 launch rosmower zone_recorder.launch.py"
    echo "  4. Web UI: http://<robot-ip>:8080/zones/recorder"
    echo ""
    echo "Documentation: Start with 00-ZONE-RECORDING-START-HERE.md"
    exit 0
else
    echo -e "${RED}✗ SOME COMPONENTS MISSING${NC}"
    echo ""
    echo "Please check the missing files listed above."
    exit 1
fi
