# Stereo Camera Setup - Jetson Orin Nano

## Hardware
- **Cameras**: 2x IMX219 CSI cameras
- **Port Assignment**:
  - Left camera → CAM0 → sensor_id=0 → /dev/video0
  - Right camera → CAM1 → sensor_id=1 → /dev/video1

## Quick Start

### 1. Check Camera Detection
```bash
# List detected cameras
v4l2-ctl --list-devices

# Should show:
# vi-output, imx219 9-0010 (platform:tegra-capture-vi:0):
#     /dev/video0
# vi-output, imx219 10-0010 (platform:tegra-capture-vi:2):
#     /dev/video1
```

### 2. Test Cameras with GStreamer
```bash
# Test left camera (sensor_id=0)
gst-launch-1.0 nvarguscamerasrc sensor_id=0 ! 'video/x-raw(memory:NVMM), width=1280, height=720, format=NV12, framerate=30/1' ! nvvidconv ! nvegltransform ! nveglglessink -e

# Test right camera (sensor_id=1)
gst-launch-1.0 nvarguscamerasrc sensor_id=1 ! 'video/x-raw(memory:NVMM), width=1280, height=720, format=NV12, framerate=30/1' ! nvvidconv ! nvegltransform ! nveglglessink -e
```

### 3. Launch ROS 2 Stereo Camera Node

#### Both cameras:
```bash
ros2 launch stereo_camera_viewer stereo_cameras.launch.py
```

#### Single camera (if one is unplugged):
```bash
# Will attempt both, but work with whichever is connected
ros2 launch stereo_camera_viewer stereo_cameras.launch.py
```

#### Custom resolution:
```bash
# 640x480 @ 60fps for higher frame rate
ros2 launch stereo_camera_viewer stereo_cameras.launch.py width:=640 height:=480 fps:=60

# 1920x1080 @ 30fps for higher quality
ros2 launch stereo_camera_viewer stereo_cameras.launch.py width:=1920 height:=1080 fps:=30
```

## Published Topics

When running, the node publishes:
- `/stereo/left/image_raw` - Left camera image (sensor_msgs/Image)
- `/stereo/right/image_raw` - Right camera image (sensor_msgs/Image)
- `/stereo/left/camera_info` - Left camera calibration (sensor_msgs/CameraInfo)
- `/stereo/right/camera_info` - Right camera calibration (sensor_msgs/CameraInfo)

## View in RViz

```bash
# Terminal 1: Launch cameras
ros2 launch stereo_camera_viewer stereo_cameras.launch.py

# Terminal 2: Launch RViz
rviz2
```

In RViz:
1. Click "Add" button
2. Select "Image" display
3. Set topic to `/stereo/left/image_raw`
4. Add another Image display for `/stereo/right/image_raw`
5. Change Fixed Frame to `stereo_camera`

## Check Topics

```bash
# List active topics
ros2 topic list | grep stereo

# Echo topic info
ros2 topic info /stereo/left/image_raw

# Monitor frame rate
ros2 topic hz /stereo/left/image_raw

# View image in terminal
ros2 run rqt_image_view rqt_image_view /stereo/left/image_raw
```

## Troubleshooting

### No cameras detected
```bash
# Check physical connections
ls -la /dev/video*

# Check kernel detection
sudo dmesg | grep imx219

# Verify user in video group
groups | grep video
```

### GStreamer errors
If you get GStreamer errors:
```bash
# Try lower resolution
ros2 launch stereo_camera_viewer stereo_cameras.launch.py width:=640 height:=480

# Or fallback to V4L2 (slower, no hardware acceleration)
ros2 launch stereo_camera_viewer stereo_cameras.launch.py use_gstreamer:=false
```

### Low FPS
```bash
# Enable max performance mode
sudo nvpmodel -m 0
sudo jetson_clocks

# Monitor system resources
tegrastats
```

### Camera upside down
```bash
# Rotate 180 degrees
ros2 launch stereo_camera_viewer stereo_cameras.launch.py flip_method:=2

# Horizontal flip
ros2 launch stereo_camera_viewer stereo_cameras.launch.py flip_method:=4
```

## Isaac ROS Integration

For Isaac ROS navigation, these topics are compatible with:
- `isaac_ros_visual_slam` - Visual SLAM
- `isaac_ros_stereo_image_proc` - Stereo depth
- `isaac_ros_nvblox` - 3D reconstruction

Example Isaac ROS integration:
```bash
# Launch cameras
ros2 launch stereo_camera_viewer stereo_cameras.launch.py

# Launch Isaac ROS Visual SLAM (in isaac_ros container)
ros2 launch isaac_ros_visual_slam isaac_ros_visual_slam.launch.py
```

## Camera Calibration (Required for accurate stereo)

```bash
# Install calibration tools
sudo apt install ros-humble-camera-calibration

# Print checkerboard (8x6, 24mm squares)
# https://calib.io/pages/camera-calibration-pattern-generator

# Run calibration
ros2 run camera_calibration cameracalibrator \
    --size 8x6 \
    --square 0.024 \
    --approximate 0.01 \
    --no-service-check \
    right:=/stereo/right/image_raw \
    left:=/stereo/left/image_raw \
    right_camera:=/stereo/right \
    left_camera:=/stereo/left

# Save calibration files to:
# ~/.ros/camera_info/
```

## Performance Tips

### Recommended Settings for Different Use Cases

**Navigation (balanced)**:
- 1280x720 @ 30fps
- Good quality, low latency

**High-speed tracking**:
- 640x480 @ 60fps
- Lower quality, higher frame rate

**High-quality mapping**:
- 1920x1080 @ 30fps
- Best quality, higher CPU usage

**Maximum performance**:
- 640x480 @ 90fps
- Lowest latency possible

## Current Status

- ✅ Left camera (video0): Working
- ⚠️ Right camera (video1): Unplugged - plug in and restart node

