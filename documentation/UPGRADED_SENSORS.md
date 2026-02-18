# Upgraded Sensors Configuration

## Hardware Upgrades

### 1. RPlidar C1 (LIDAR)
- **Model**: SLAMTEC RPlidar C1
- **Connection**: USB Serial (CP2102 chip)
- **Baud Rate**: 460800 (upgraded from A1's 115200)
- **Device Path**: `/dev/ttyUSB0` or `/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0`
- **Scan Mode**: Standard
- **Features**:
  - 8m range
  - 360° scanning
  - ~8-10 Hz scan rate
  - Better obstacle detection than A1

### 2. Stereo CSI Cameras (IMX219)
- **Model**: IMX219 (dual cameras)
- **Connection**: CSI (Camera Serial Interface) on Jetson
- **Devices**:
  - Left Camera: `/dev/video1` (CAM1 port)
  - Right Camera: `/dev/video2` (CAM0 port)
- **Resolution**: 1280x720 @ 30 FPS (configurable)
- **Pipeline**: GStreamer with hardware acceleration (nvarguscamerasrc)
- **Features**:
  - Stereo vision for depth perception
  - Hardware-accelerated encoding
  - Compressed image transport for bandwidth efficiency

## ROS2 Configuration Changes

### Launch File Updates (`launch_robot.launch.py`)

#### RPlidar C1:
```python
rplidar_node = Node(
    package='sllidar_ros2',
    executable='sllidar_node',
    name='rplidar',
    parameters=[{
        'serial_port': '/dev/serial/by-id/usb-Silicon_Labs_CP2102_...',
        'serial_baudrate': 460800,  # ← CHANGED from 115200
        'frame_id': 'laser_frame',
        'scan_mode': 'Standard',
        'angle_compensate': True,
    }]
)
```

#### Stereo Cameras:
```python
stereo_camera_node = Node(
    package='stereo_camera_viewer',
    executable='stereo_camera_node',
    name='stereo_camera_node',
    parameters=[{
        'left_camera_id': 1,        # /dev/video1
        'right_camera_id': 2,       # /dev/video2
        'width': 1280,
        'height': 720,
        'fps': 30,
        'use_gstreamer': True,      # Hardware acceleration
        'frame_id': 'stereo_camera',
        'jpeg_quality': 80
    }]
)
```

## Published ROS2 Topics

### LIDAR Topics
| Topic | Message Type | Rate | Description |
|-------|-------------|------|-------------|
| `/scan` | `sensor_msgs/LaserScan` | ~8-10 Hz | 360° laser scan data |

### Camera Topics
| Topic | Message Type | Rate | Description |
|-------|-------------|------|-------------|
| `/stereo/left/image_raw` | `sensor_msgs/Image` | 30 Hz | Left camera raw image |
| `/stereo/right/image_raw` | `sensor_msgs/Image` | 30 Hz | Right camera raw image |
| `/stereo/left/image_raw/compressed` | `sensor_msgs/CompressedImage` | 30 Hz | Left camera JPEG compressed |
| `/stereo/right/image_raw/compressed` | `sensor_msgs/CompressedImage` | 30 Hz | Right camera JPEG compressed |
| `/stereo/left/camera_info` | `sensor_msgs/CameraInfo` | 30 Hz | Left camera calibration |
| `/stereo/right/camera_info` | `sensor_msgs/CameraInfo` | 30 Hz | Right camera calibration |

## TF Frames

### Added Static Transforms
- `base_link` → `laser_frame` (LIDAR position: x=0.20, y=0, z=0.25)
- `base_link` → `stereo_camera_left` (Left camera: x=0.15, y=0.06, z=0.15)
- `base_link` → `stereo_camera_right` (Right camera: x=0.15, y=-0.06, z=0.15)

**Note**: Adjust these transforms based on your actual physical mounting positions!

## Testing the Upgrades

### 1. Hardware Detection
```bash
# Check LIDAR
ls -l /dev/ttyUSB*
ls -l /dev/serial/by-id/*CP2102*

# Check Cameras
ls -l /dev/video*
v4l2-ctl --list-devices | grep imx219
```

### 2. Run Comprehensive Test
```bash
./test_sensors_upgraded.sh
```

This script will:
- Verify hardware device detection
- Check Docker container status
- Confirm ROS2 nodes are running
- Test all sensor topics are publishing
- Measure publishing rates
- Verify TF frames

### 3. Manual Topic Testing
```bash
# Inside Docker container (or use docker exec)
./docker-helper.sh shell

# Check LIDAR
ros2 topic echo /scan --once
ros2 topic hz /scan

# Check Left Camera
ros2 topic echo /stereo/left/image_raw --once
ros2 topic hz /stereo/left/image_raw

# Check Right Camera
ros2 topic echo /stereo/right/image_raw --once
ros2 topic hz /stereo/right/image_raw

# Check compressed images (better for web viewing)
ros2 topic hz /stereo/left/image_raw/compressed
ros2 topic hz /stereo/right/image_raw/compressed
```

## Visualization with RViz

### Launch RViz
```bash
./docker-helper.sh rviz
```

### Add Displays
1. **LaserScan**: 
   - Add → LaserScan
   - Topic: `/scan`
   - Fixed Frame: `laser_frame` or `base_link`

2. **Left Camera**:
   - Add → Image
   - Topic: `/stereo/left/image_raw`

3. **Right Camera**:
   - Add → Image
   - Topic: `/stereo/right/image_raw`

4. **TF Tree**:
   - Add → TF
   - Shows camera and LIDAR frames relative to base_link

## Integration with Mower Navigation

### LIDAR for Obstacle Avoidance
The RPlidar C1 publishes `/scan` which Nav2 uses for:
- Costmap obstacle layer
- Dynamic obstacle detection
- Real-time path re-planning

### Stereo Cameras for Visual Navigation
Potential uses (requires additional processing nodes):
- **Depth estimation**: Compute point cloud from stereo pairs
- **Visual odometry**: Track motion using camera features
- **AprilTag detection**: Dock detection and alignment
- **Terrain classification**: Grass vs. obstacles
- **Object recognition**: Detect pets, people, toys

## Camera Calibration (Recommended)

For accurate stereo vision, calibrate the cameras:

```bash
# Install camera calibration tools
sudo apt install ros-humble-camera-calibration

# Run calibration (checkerboard pattern required)
ros2 run camera_calibration cameracalibrator \
    --size 8x6 \
    --square 0.024 \
    --ros-args \
    -r right:=/stereo/right/image_raw \
    -r left:=/stereo/left/image_raw
```

Save calibration files to:
- `/opt/ros/humble/share/stereo_camera_viewer/config/left_camera.yaml`
- `/opt/ros/humble/share/stereo_camera_viewer/config/right_camera.yaml`

## Troubleshooting

### LIDAR Not Detected
```bash
# Check USB permissions
sudo chmod 666 /dev/ttyUSB0

# Check if device exists
lsusb | grep -i "Silicon Labs"

# Test serial communication
minicom -D /dev/ttyUSB0 -b 460800
```

### Cameras Not Detected
```bash
# Check CSI connection (Jetson-specific)
v4l2-ctl --list-devices

# Test GStreamer pipeline
gst-launch-1.0 nvarguscamerasrc sensor-id=1 ! \
    'video/x-raw(memory:NVMM),width=1280,height=720,framerate=30/1' ! \
    nvvidconv ! autovideosink

# Check camera permissions
sudo usermod -aG video $USER
```

### Low Frame Rate
```bash
# Reduce resolution
width: 640
height: 480

# Reduce FPS
fps: 15

# Disable raw image, use only compressed
# (modify stereo_camera_node.py to skip raw publishers)
```

### High CPU Usage
```bash
# Ensure GStreamer hardware acceleration is enabled
use_gstreamer: True

# Use compressed topics for network transmission
# Subscribe to /stereo/*/image_raw/compressed instead of /stereo/*/image_raw
```

## Performance Optimization

### For Mowing Operations
- Use compressed image topics over network
- Reduce camera FPS to 15 if CPU constrained
- Process stereo depth at lower resolution (640x480)
- LIDAR is critical—prioritize /scan topic

### Bandwidth Considerations
- Raw image @ 30 FPS: ~90 MB/s per camera
- Compressed image @ 30 FPS: ~3-5 MB/s per camera
- LIDAR /scan: ~50 KB/s

**Recommendation**: Use compressed topics for web UI and remote monitoring.

## Next Steps for Advanced Features

1. **Stereo Depth Processing**:
   - Add `stereo_image_proc` node for disparity/point cloud
   - Topics: `/stereo/disparity`, `/stereo/points2`

2. **Visual Odometry**:
   - Integrate `rtabmap_ros` or `viso2_ros`
   - Fuse with wheel odometry in EKF

3. **AprilTag Dock Detection**:
   - Add `apriltag_ros` package
   - Detect charging dock for autonomous return

4. **Object Detection**:
   - Add YOLOv5/v8 or TensorRT inference
   - Detect pets, people, toys to avoid

5. **Terrain Classification**:
   - Train CNN to distinguish grass/pavement/obstacles
   - Adaptive mowing patterns

## Files Modified

- `src/rosmower/launch/launch_robot.launch.py` - Updated LIDAR baud rate and stereo camera integration
- Created `test_sensors_upgraded.sh` - Comprehensive sensor test script
- Created `UPGRADED_SENSORS.md` - This documentation

## Configuration Summary

| Setting | Old (A1 + Single Camera) | New (C1 + Stereo) |
|---------|--------------------------|-------------------|
| LIDAR Baud | 115200 | 460800 |
| LIDAR Range | 6m | 8m |
| Camera Count | 1 (USB) | 2 (CSI) |
| Camera Resolution | 640x480 | 1280x720 |
| Camera Pipeline | V4L2 | GStreamer (HW accel) |
| Stereo Vision | No | Yes |

---

**Version**: 1.0  
**Date**: 2026-02-15  
**Hardware**: Jetson Nano/Xavier + RPlidar C1 + Dual IMX219 CSI Cameras
