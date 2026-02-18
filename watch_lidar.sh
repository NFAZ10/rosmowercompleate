#!/bin/bash
# Continuous LiDAR health monitor - detects when it stops

echo "=== C1M1 LiDAR Continuous Monitor ==="
echo "Watching for intermittent shutdowns..."
echo "Press Ctrl+C to stop"
echo ""

LOG_FILE="/tmp/lidar_health_$(date +%Y%m%d_%H%M%S).log"
echo "Logging to: $LOG_FILE"

# Initialize counters
HEALTHY_COUNT=0
FAILURE_COUNT=0
LAST_STATUS="unknown"

while true; do
    TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Check if node is running
    NODE_RUNNING=$(docker exec rosmower_bridge bash -c "source /opt/ros/humble/setup.bash && ros2 node list 2>/dev/null" | grep -c sllidar_node)
    
    # Check if scan topic is publishing
    TOPIC_HZ=$(timeout 3 docker exec rosmower_bridge bash -c "source /opt/ros/humble/setup.bash && ros2 topic hz /scan 2>&1" | grep -oP 'average rate: \K[0-9.]+' | head -1)
    
    if [ -n "$TOPIC_HZ" ] && [ "$NODE_RUNNING" -gt 0 ]; then
        HEALTHY_COUNT=$((HEALTHY_COUNT + 1))
        STATUS="✓ HEALTHY"
        RATE_MSG="(${TOPIC_HZ} Hz)"
        
        if [ "$LAST_STATUS" != "healthy" ]; then
            echo "$TIMESTAMP - $STATUS - LiDAR recovered! $RATE_MSG" | tee -a "$LOG_FILE"
            echo "$TIMESTAMP - RECOVERY - Node: $NODE_RUNNING, Rate: $TOPIC_HZ Hz" >> "$LOG_FILE"
        else
            # Only print every 10th healthy check to reduce spam
            if [ $((HEALTHY_COUNT % 10)) -eq 0 ]; then
                echo "$TIMESTAMP - $STATUS $RATE_MSG [checks: $HEALTHY_COUNT]"
            fi
        fi
        LAST_STATUS="healthy"
    else
        FAILURE_COUNT=$((FAILURE_COUNT + 1))
        STATUS="✗ FAILED"
        
        echo "" | tee -a "$LOG_FILE"
        echo "======================================" | tee -a "$LOG_FILE"
        echo "$TIMESTAMP - $STATUS - LiDAR stopped!" | tee -a "$LOG_FILE"
        echo "  Node running: $NODE_RUNNING" | tee -a "$LOG_FILE"
        echo "  Topic rate: ${TOPIC_HZ:-NONE}" | tee -a "$LOG_FILE"
        echo "  Failure count: $FAILURE_COUNT" | tee -a "$LOG_FILE"
        
        # Check USB device status
        if [ -e /dev/rplidar ]; then
            echo "  USB device: EXISTS" | tee -a "$LOG_FILE"
        else
            echo "  USB device: MISSING!" | tee -a "$LOG_FILE"
        fi
        
        # Check last kernel messages
        echo "  Last USB messages:" | tee -a "$LOG_FILE"
        sudo dmesg | grep -i "usb\|ttyUSB" | tail -5 | sed 's/^/    /' | tee -a "$LOG_FILE"
        
        echo "======================================" | tee -a "$LOG_FILE"
        echo "" | tee -a "$LOG_FILE"
        
        LAST_STATUS="failed"
    fi
    
    sleep 3
done
