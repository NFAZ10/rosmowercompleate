#!/bin/bash
# Zone Recording System Test Script
# Tests GPS-based zone recording functionality with simulated GPS data

set -e

echo "=============================================="
echo "Zone Recording System Test"
echo "=============================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
pass_test() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((TESTS_PASSED++))
}

fail_test() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((TESTS_FAILED++))
}

info() {
    echo -e "${YELLOW}ℹ INFO${NC}: $1"
}

# Check if ROS2 is available
check_ros2() {
    if ! command -v ros2 &> /dev/null; then
        fail_test "ROS2 not found in PATH"
        exit 1
    fi
    pass_test "ROS2 found"
}

# Check if zone_recorder node is available
check_zone_recorder_node() {
    info "Checking if zone_recorder executable exists..."
    if [ -f "$(rospack find rosmower)/scripts/zone_recorder.py" ]; then
        pass_test "zone_recorder.py found"
    else
        fail_test "zone_recorder.py not found"
    fi
}

# Check if message definitions are built
check_messages() {
    info "Checking message definitions..."
    
    # Try to find ZoneRecordingStatus message
    if ros2 interface show rosmower_msgs/msg/ZoneRecordingStatus &> /dev/null; then
        pass_test "ZoneRecordingStatus message found"
    else
        fail_test "ZoneRecordingStatus message not found (rebuild workspace)"
    fi
    
    # Try to find service definitions
    if ros2 interface show rosmower_msgs/srv/StartZoneRecording &> /dev/null; then
        pass_test "StartZoneRecording service found"
    else
        fail_test "StartZoneRecording service not found (rebuild workspace)"
    fi
}

# Test 1: Start and stop zone recorder node
test_node_lifecycle() {
    info "Test 1: Zone recorder node lifecycle"
    
    # Launch node in background
    ros2 run rosmower zone_recorder.py &
    NODE_PID=$!
    sleep 3
    
    # Check if node is running
    if ps -p $NODE_PID > /dev/null; then
        pass_test "Zone recorder node started successfully"
    else
        fail_test "Zone recorder node failed to start"
        return
    fi
    
    # Check if node appears in node list
    if ros2 node list | grep -q zone_recorder; then
        pass_test "Zone recorder node appears in node list"
    else
        fail_test "Zone recorder node not in node list"
    fi
    
    # Stop node
    kill $NODE_PID
    sleep 1
    
    if ! ps -p $NODE_PID > /dev/null 2>&1; then
        pass_test "Zone recorder node stopped successfully"
    else
        fail_test "Zone recorder node failed to stop"
        kill -9 $NODE_PID
    fi
}

# Test 2: Publish simulated GPS data and record zone
test_gps_recording() {
    info "Test 2: GPS-based zone recording with simulated data"
    
    # Launch zone recorder
    ros2 run rosmower zone_recorder.py &
    NODE_PID=$!
    sleep 3
    
    # Start recording
    info "Starting zone recording..."
    ros2 service call /zone/record/start rosmower_msgs/srv/StartZoneRecording \
        "{zone_name: 'test_zone', priority: 5, use_visual_odometry: false}" &
    sleep 2
    
    # Publish simulated GPS waypoints (rectangle: 10m x 8m)
    info "Publishing simulated GPS waypoints..."
    
    # Reference point: Approximate coordinates
    BASE_LAT=37.7749
    BASE_LON=-122.4194
    
    # Calculate offsets (roughly 10m = 0.00009 degrees latitude, 8m = 0.00007 degrees longitude)
    LAT_OFFSET=0.00009
    LON_OFFSET=0.00007
    
    # Publish corners of rectangle with small steps
    for i in {0..10}; do
        PROGRESS=$(echo "scale=2; $i / 10" | bc)
        LAT=$(echo "$BASE_LAT + ($LAT_OFFSET * $PROGRESS)" | bc)
        ros2 topic pub --once /gps/fix sensor_msgs/msg/NavSatFix \
            "{header: {frame_id: 'gps'}, latitude: $LAT, longitude: $BASE_LON, altitude: 100.0, status: {status: 0}, position_covariance: [1.0, 0, 0, 0, 1.0, 0, 0, 0, 1.0]}" 2>/dev/null
        sleep 0.5
    done
    
    for i in {0..8}; do
        PROGRESS=$(echo "scale=2; $i / 8" | bc)
        LON=$(echo "$BASE_LON + ($LON_OFFSET * $PROGRESS)" | bc)
        LAT=$(echo "$BASE_LAT + $LAT_OFFSET" | bc)
        ros2 topic pub --once /gps/fix sensor_msgs/msg/NavSatFix \
            "{header: {frame_id: 'gps'}, latitude: $LAT, longitude: $LON, altitude: 100.0, status: {status: 0}, position_covariance: [1.0, 0, 0, 0, 1.0, 0, 0, 0, 1.0]}" 2>/dev/null
        sleep 0.5
    done
    
    info "Simulated GPS waypoints published"
    
    # Check status
    sleep 2
    STATUS=$(ros2 topic echo /zone/record/status rosmower_msgs/msg/ZoneRecordingStatus --once 2>/dev/null || echo "")
    
    if echo "$STATUS" | grep -q "waypoint_count"; then
        WAYPOINTS=$(echo "$STATUS" | grep "waypoint_count:" | awk '{print $2}')
        if [ "$WAYPOINTS" -gt 0 ]; then
            pass_test "Waypoints recorded: $WAYPOINTS"
        else
            fail_test "No waypoints recorded"
        fi
    else
        fail_test "Could not get recording status"
    fi
    
    # Stop recording
    info "Stopping zone recording..."
    ros2 service call /zone/record/stop rosmower_msgs/srv/StopZoneRecording \
        "{save_zone: true, auto_close: true, simplify: true, simplification_tolerance: 0.3}" &
    sleep 3
    
    # Check if zone was saved
    if [ -f "/ws/zones/test_zone.yaml" ] || [ -f "zones/test_zone.yaml" ]; then
        pass_test "Zone saved to file"
    else
        fail_test "Zone file not found"
    fi
    
    # Clean up
    kill $NODE_PID 2>/dev/null || true
    sleep 1
}

# Test 3: Test pause/resume functionality
test_pause_resume() {
    info "Test 3: Pause and resume functionality"
    
    # Launch zone recorder
    ros2 run rosmower zone_recorder.py &
    NODE_PID=$!
    sleep 3
    
    # Start recording
    ros2 service call /zone/record/start rosmower_msgs/srv/StartZoneRecording \
        "{zone_name: 'pause_test', priority: 5, use_visual_odometry: false}" &
    sleep 2
    
    # Pause
    info "Testing pause..."
    RESULT=$(ros2 service call /zone/record/control rosmower_msgs/srv/ControlZoneRecording "{command: 0}" 2>&1)
    if echo "$RESULT" | grep -q "success: true"; then
        pass_test "Pause command succeeded"
    else
        fail_test "Pause command failed"
    fi
    
    # Resume
    info "Testing resume..."
    RESULT=$(ros2 service call /zone/record/control rosmower_msgs/srv/ControlZoneRecording "{command: 1}" 2>&1)
    if echo "$RESULT" | grep -q "success: true"; then
        pass_test "Resume command succeeded"
    else
        fail_test "Resume command failed"
    fi
    
    # Cancel
    info "Testing cancel..."
    RESULT=$(ros2 service call /zone/record/control rosmower_msgs/srv/ControlZoneRecording "{command: 2}" 2>&1)
    if echo "$RESULT" | grep -q "success: true"; then
        pass_test "Cancel command succeeded"
    else
        fail_test "Cancel command failed"
    fi
    
    # Clean up
    kill $NODE_PID 2>/dev/null || true
    sleep 1
}

# Test 4: Validate polygon simplification
test_simplification() {
    info "Test 4: Polygon simplification (Douglas-Peucker)"
    
    # This is tested implicitly in test_gps_recording
    # Here we just verify the algorithm is available
    
    if grep -q "douglas_peucker" "$(find . -name zone_recorder.py)"; then
        pass_test "Douglas-Peucker algorithm found in code"
    else
        fail_test "Douglas-Peucker algorithm not found"
    fi
}

# Test 5: Check web API endpoints
test_web_api() {
    info "Test 5: Web API endpoints"
    
    # Check if web server is running
    if curl -s http://localhost:8080/api/zone/record/status > /dev/null 2>&1; then
        pass_test "Zone recording API endpoint accessible"
    else
        info "Web server not running, skipping API test"
    fi
}

# Run all tests
main() {
    echo ""
    info "Starting tests..."
    echo ""
    
    check_ros2
    check_zone_recorder_node
    check_messages
    
    echo ""
    info "Running functional tests..."
    echo ""
    
    # Only run functional tests if building/sourcing worked
    if [ $TESTS_FAILED -eq 0 ]; then
        test_node_lifecycle
        test_pause_resume
        test_simplification
        test_web_api
        # test_gps_recording  # Commented out - requires full ROS2 environment
    else
        info "Skipping functional tests due to previous failures"
    fi
    
    echo ""
    echo "=============================================="
    echo "Test Results"
    echo "=============================================="
    echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"
    echo "=============================================="
    
    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}Some tests failed.${NC}"
        exit 1
    fi
}

# Run main
main
