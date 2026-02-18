#!/bin/bash
# Quick system status check for ROSmower

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          ROSmower Full Stack Status                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Check containers
echo "📦 Docker Containers:"
docker ps --filter "name=rosmower" --format "  ✓ {{.Names}} - {{.Status}}"
echo ""

# Check if in container
if docker exec rosmower_launch bash -c "source /opt/ros/humble/setup.bash && ros2 node list" &>/dev/null; then
    # Count nodes
    NODE_COUNT=$(docker exec rosmower_launch bash -c "source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && ros2 node list 2>/dev/null | wc -l")
    echo "🤖 ROS2 System: $NODE_COUNT nodes active"
    echo ""
    
    echo "🔑 Core Nodes:"
    docker exec rosmower_launch bash -c "source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && ros2 node list 2>/dev/null | grep -E 'hoverboard|rplidar|gps|imu|battery|mode_manager|rosbridge'" | sed 's/^/  ✓ /'
    echo ""
    
    echo "📡 Key Topics:"
    docker exec rosmower_launch bash -c "source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && ros2 topic list 2>/dev/null | grep -E '^/(scan|cmd_vel|odom|gps/fix|imu/data|battery_state|joint_states|camera/image)'" | sed 's/^/  ✓ /'
    echo ""
    
    echo "🌐 Web Interface:"
    if docker exec rosmower_launch bash -c "source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && ros2 node list 2>/dev/null" | grep -q rosbridge; then
        echo "  ✓ rosbridge running on ws://localhost:9090"
        echo "  ✓ Control UI: http://localhost:8080/"
        echo "  ✓ Routes UI: http://localhost:8080/routes"
    else
        echo "  ⚠️  rosbridge not running (start with: docker-helper.sh bridge -d)"
    fi
else
    echo "⚠️  ROS2 system not responding"
fi

echo ""
echo "─────────────────────────────────────────────────────────────"
echo "Commands:"
echo "  View logs:     docker logs rosmower_launch -f"
echo "  Stop system:   docker stop rosmower_launch rosmower_zenoh"
echo "  Restart:       docker restart rosmower_launch"
echo "  Shell access:  docker exec -it rosmower_launch bash"
echo "─────────────────────────────────────────────────────────────"
