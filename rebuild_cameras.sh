#!/bin/bash
# Quick rebuild and test script for camera changes
# Run this after modifications to stereo camera node

set -e

echo "════════════════════════════════════════════"
echo "  Camera Node Rebuild & Test"
echo "════════════════════════════════════════════"
echo ""

# 1. Rebuild packages
echo "1️⃣  Building stereo_camera_viewer and rosmower packages..."
colcon build --packages-select stereo_camera_viewer rosmower --symlink-install
echo "✓ Build complete"
echo ""

# 2. Source environment
echo "2️⃣  Sourcing ROS2 environment..."
source install/setup.bash
echo "✓ Environment sourced"
echo ""

# 3. Test GStreamer (optional)
if command -v gst-launch-1.0 &> /dev/null; then
    echo "3️⃣  Testing GStreamer cameras (3 seconds each)..."
    ./test_gstreamer_cameras.sh || echo "⚠️  GStreamer test had warnings (may be normal)"
    echo ""
else
    echo "3️⃣  Skipping GStreamer test (not in Docker or native environment)"
    echo ""
fi

# 4. Launch instructions
echo "════════════════════════════════════════════"
echo "✅ Ready to launch!"
echo ""
echo "Test with cameras enabled:"
echo "  ros2 launch rosmower launch_robot.launch.py use_stereo_camera:=true"
echo ""
echo "Test without cameras (if still having issues):"
echo "  ros2 launch rosmower launch_robot.launch.py use_stereo_camera:=false"
echo ""
echo "Monitor topics:"
echo "  ros2 topic list | grep stereo"
echo "  ros2 topic hz /stereo/left/image_raw/compressed"
echo "  ros2 topic bw /stereo/left/image_raw/compressed"
echo ""
echo "Monitor performance (in Docker or native):"
echo "  jtop  # Real-time GPU/CPU/memory monitoring"
echo "════════════════════════════════════════════"
