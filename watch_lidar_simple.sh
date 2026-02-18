#!/bin/bash
# watch_lidar_simple.sh - Monitor LiDAR without sudo prompts

echo "=== C1M1 LiDAR Health Monitor ==="
echo "Monitoring /scan topic every 5 seconds..."
echo "Will report when LiDAR stops or resumes"
echo ""

COUNT=0
LAST_STATE="unknown"

while true; do
    COUNT=$((COUNT + 1))
    TIME=$(date '+%H:%M:%S')
    
    # Check topic rate
    RATE=$(timeout 4 docker exec rosmower_bridge bash -c "source /opt/ros/humble/setup.bash && ros2 topic hz /scan 2>&1" | grep "average rate" | head -1 | grep -oP '[0-9]+\.[0-9]+' | head -1)
    
    if [ -n "$RATE" ]; then
        if [ "$LAST_STATE" != "ok" ]; then
            echo "[$TIME] ✓ LIDAR RESUMED - ${RATE} Hz"
        else
            # Print every 5th check when healthy
            if [ $((COUNT % 5)) == 0 ]; then
                echo "[$TIME] ✓ OK - ${RATE} Hz [check #$COUNT]"
            fi
        fi
        LAST_STATE="ok"
    else
        echo "[$TIME] ✗ LIDAR STOPPED - No scan data!"
        LAST_STATE="fail"
    fi
    
    sleep 5
done
