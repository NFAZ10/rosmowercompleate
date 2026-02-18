#!/bin/bash
# Test GStreamer camera pipelines on Jetson
# Helps diagnose camera issues before launching ROS2 nodes

echo "═══════════════════════════════════════════════"
echo "  Jetson Camera GStreamer Diagnostics"
echo "═══════════════════════════════════════════════"
echo ""

echo "1. Testing Left Camera (sensor-id=0)..."
timeout 3 gst-launch-1.0 nvarguscamerasrc sensor-id=0 num-buffers=30 ! \
    'video/x-raw(memory:NVMM), width=640, height=480, framerate=15/1' ! \
    nvvidconv ! 'video/x-raw, format=BGRx' ! videoconvert ! fakesink sync=false 2>&1 | \
    grep -E "(Setting|ERROR|WARN)" || echo "✓ Left camera OK"

echo ""
echo "2. Testing Right Camera (sensor-id=1)..."
timeout 3 gst-launch-1.0 nvarguscamerasrc sensor-id=1 num-buffers=30 ! \
    'video/x-raw(memory:NVMM), width=640, height=480, framerate=15/1' ! \
    nvvidconv ! 'video/x-raw, format=BGRx' ! videoconvert ! fakesink sync=false 2>&1 | \
    grep -E "(Setting|ERROR|WARN)" || echo "✓ Right camera OK"

echo ""
echo "3. Available video devices:"
v4l2-ctl --list-devices 2>/dev/null || echo "v4l2-ctl not available"

echo ""
echo "4. Memory/Performance check:"
free -h | grep -E "(Mem|Swap)"

echo ""
echo "5. GPU/VIC status:"
cat /sys/kernel/debug/bpmp/debug/clk/vic/rate 2>/dev/null | awk '{printf "VIC clock: %.0f MHz\n", $1/1000000}' || echo "VIC status unavailable"
cat /sys/kernel/debug/bpmp/debug/clk/nvenc/rate 2>/dev/null | awk '{printf "NVENC clock: %.0f MHz\n", $1/1000000}' || echo "NVENC status unavailable"

echo ""
echo "═══════════════════════════════════════════════"
echo "If cameras show errors, check:"
echo "  • Camera ribbons properly seated"
echo "  • Correct sensor-id (0 = CAM0, 1 = CAM1)"
echo "  • Docker has --privileged or device access"
echo "═══════════════════════════════════════════════"
