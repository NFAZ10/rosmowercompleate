#!/bin/bash

# Script to verify camera devices are accessible in the container

echo "=== Camera Device Detection ==="
echo ""

# Check for video devices
echo "Video devices on host:"
ls -la /dev/video* 2>/dev/null || echo "No /dev/video* devices found"
echo ""

# Check device permissions
echo "Device permissions:"
for dev in /dev/video0 /dev/video1 /dev/video2 /dev/video3; do
    if [ -e "$dev" ]; then
        ls -l "$dev"
    fi
done
echo ""

# Check v4l2 capabilities
if command -v v4l2-ctl &> /dev/null; then
    echo "V4L2 device list:"
    v4l2-ctl --list-devices
    echo ""
else
    echo "v4l2-ctl not installed (install with: apt install v4l-utils)"
    echo ""
fi

# Check for CSI cameras (Jetson specific)
echo "Checking for CSI cameras (Jetson):"
if command -v nvgstcapture-1.0 &> /dev/null; then
    echo "nvgstcapture-1.0 found - CSI cameras may be available"
    echo "Test with: nvgstcapture-1.0 --sensor-id=0"
else
    echo "nvgstcapture-1.0 not found (CSI camera tools not installed)"
fi
echo ""

# Check dmesg for camera info
echo "Recent camera-related kernel messages:"
dmesg | grep -i -E "video|camera|imx|csi" | tail -20
echo ""

# Check if running in Docker
if [ -f /.dockerenv ]; then
    echo "Running inside Docker container ✓"
else
    echo "Running on host (not in container)"
fi
echo ""

# Test camera access with Python
if command -v python3 &> /dev/null; then
    echo "Testing camera access with OpenCV:"
    python3 - << 'EOF'
import sys
try:
    import cv2
    for i in range(4):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret:
                print(f"  ✓ /dev/video{i} - Working ({frame.shape[1]}x{frame.shape[0]})")
            else:
                print(f"  ⚠ /dev/video{i} - Opens but can't read frames")
            cap.release()
        else:
            print(f"  ✗ /dev/video{i} - Cannot open")
except ImportError:
    print("  OpenCV not installed (install with: pip3 install opencv-python)")
except Exception as e:
    print(f"  Error: {e}")
EOF
else
    echo "Python3 not available for testing"
fi
echo ""

echo "=== Recommendations ==="
echo "1. Ensure cameras are connected and detected on host"
echo "2. Check camera permissions: sudo chmod 666 /dev/video*"
echo "3. Add user to video group: sudo usermod -aG video \$USER"
echo "4. For Docker: Restart container after device changes"
echo "5. For Jetson CSI: Ensure nvarguscamerasrc is available"
