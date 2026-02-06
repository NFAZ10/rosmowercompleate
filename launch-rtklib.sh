#!/bin/bash
# Quick launcher for RTKLIB RTK GPS with ROS2
# Usage: ./launch-rtklib.sh [options]
# Options:
#   --no-rtklib    Launch ROS2 GPS node without starting RTKLIB rtkrcv
#   --help         Show this help message

set -e

WORKSPACE="/workspaces/rosmowercompleate"
START_RTKLIB="true"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-rtklib)
            START_RTKLIB="false"
            shift
            ;;
        --help)
            grep "^#" "$0" | tail -n +2
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "🚀 Launching RTKLIB RTK GPS System..."
echo "   START_RTKLIB=$START_RTKLIB"
echo ""

# Enter Isaac ROS container and launch
bash -i -c "dh dev && source /workspaces/rosmowercompleate/install/setup.bash && ros2 launch gps_rtk rtklib.launch.py start_rtklib:=$START_RTKLIB"
