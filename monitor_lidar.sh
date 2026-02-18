#!/bin/bash
# Monitor C1M1 LiDAR scan topic

echo "=== SLAMTEC C1M1 LiDAR Monitor ==="
echo ""
echo "Launching LiDAR with 460800 baud (C1M1 standard)..."
echo ""

# Launch in background
docker exec -d rosmower_bridge bash -c "
    source /opt/ros/humble/setup.bash && 
    source /ws/install/setup.bash && 
    ros2 launch sllidar_ros2 sllidar_c1_launch.py \
        serial_port:=/dev/rplidar \
        serial_baudrate:=460800
"

sleep 5

echo ""
echo "=== Checking ROS Topics ===" 
docker exec rosmower_bridge bash -c "
    source /opt/ros/humble/setup.bash && 
    ros2 topic list
"

echo ""
echo "=== Monitoring /scan topic for 20 seconds ==="
echo "Press Ctrl+C to stop"
echo ""

timeout 20 docker exec rosmower_bridge bash -c "
    source /opt/ros/humble/setup.bash && 
    ros2 topic hz /scan
" || echo "Scan topic monitoring ended"

echo ""
echo "=== Sample scan data ==="
docker exec rosmower_bridge bash -c "
    source /opt/ros/humble/setup.bash && 
    ros2 topic echo /scan --once --no-arr
" 2>&1 | head -50

echo ""
echo "=== Node info ==="
docker exec rosmower_bridge bash -c "
    source /opt/ros/humble/setup.bash && 
    ros2 node info /sllidar_node
" 2>&1 | head -30
