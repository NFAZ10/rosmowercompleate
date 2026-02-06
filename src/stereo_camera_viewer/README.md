# Stereo Camera Viewer for Jetson

ROS2 package for viewing stereo cameras on NVIDIA Jetson platforms with hardware acceleration support.

## Features

- **Hardware Acceleration** - GStreamer pipeline with NVMM for CSI cameras
- **Dual Camera Support** - Left and right camera streams
- **Real-time Viewing** - OpenCV-based viewer with FPS display
- **Flexible Input** - Supports both CSI (MIPI) and USB cameras
- **Standard ROS Topics** - Publishes sensor_msgs/Image and CameraInfo

## Hardware Setup

### CSI (MIPI) Cameras on Jetson

For dual CSI cameras (like dual IMX219, IMX477, etc.):

1. **Connect cameras to CSI ports:**
   - Left camera → CAM0 (or CAM1)
   - Right camera → CAM1 (or CAM0)

2. **Verify camera detection:**
   ```bash
   ls /dev/video*
   # Should show video0, video1, etc.
   
   # For more details:
   v4l2-ctl --list-devices
   ```

3. **Test cameras individually:**
   ```bash
   # Test camera 0
   nvgstcapture-1.0 --sensor-id=0
   
   # Test camera 1
   nvgstcapture-1.0 --sensor-id=1
   ```

### USB Cameras

For USB stereo cameras:
1. Connect both USB cameras
2. Check device assignments: `ls -l /dev/video*`
3. Set `use_gstreamer: false` in config
4. Update camera IDs based on /dev/video* indices

## Installation

1. **Install dependencies:**
   ```bash
   sudo apt-get update
   sudo apt-get install -y \
       python3-opencv \
       ros-humble-cv-bridge \
       ros-humble-image-transport \
       ros-humble-camera-info-manager
   ```

2. **Build the package:**
   ```bash
   cd /mnt/nova_ssd/rosmowercompleate
   colcon build --packages-select stereo_camera_viewer
   source install/setup.bash
   ```

## Usage

### Quick Start - View Stereo Cameras

```bash
ros2 launch stereo_camera_viewer stereo_view.launch.py
```

This will:
- Start publishing camera images
- Open two OpenCV windows showing left and right cameras
- Display FPS on each camera view

### Custom Resolution

```bash
# 1080p @ 30fps
ros2 launch stereo_camera_viewer stereo_view.launch.py width:=1920 height:=1080 fps:=30

# VGA @ 60fps
ros2 launch stereo_camera_viewer stereo_view.launch.py width:=640 height:=480 fps:=60
```

### USB Cameras

```bash
ros2 launch stereo_camera_viewer stereo_view.launch.py use_gstreamer:=false
```

### Without Viewer (Publish Only)

```bash
ros2 launch stereo_camera_viewer stereo_view.launch.py show_viewer:=false
```

### Run Components Separately

```bash
# Terminal 1: Start camera publisher
ros2 run stereo_camera_viewer stereo_camera_node

# Terminal 2: Start viewer
ros2 run stereo_camera_viewer simple_viewer
```

## Published Topics

- `/stereo/left/image_raw` - Left camera image (sensor_msgs/Image)
- `/stereo/right/image_raw` - Right camera image (sensor_msgs/Image)
- `/stereo/left/camera_info` - Left camera calibration (sensor_msgs/CameraInfo)
- `/stereo/right/camera_info` - Right camera calibration (sensor_msgs/CameraInfo)

## Viewing Options

### 1. Built-in OpenCV Viewer

The simple_viewer shows both cameras with FPS overlay:
```bash
ros2 run stereo_camera_viewer simple_viewer
```

**Controls:**
- `q` - Quit
- `s` - Save stereo pair (future feature)

### 2. ROS2 Image View

View individual cameras:
```bash
# View left camera
ros2 run rqt_image_view rqt_image_view /stereo/left/image_raw

# View right camera
ros2 run rqt_image_view rqt_image_view /stereo/right/image_raw
```

### 3. RViz2

```bash
rviz2
```
Then add Image displays for:
- `/stereo/left/image_raw`
- `/stereo/right/image_raw`

### 4. Side-by-Side View

Use `stereo_image_proc`:
```bash
sudo apt install ros-humble-stereo-image-proc
ros2 run stereo_image_proc stereo_image_proc
```

## Camera Calibration

For accurate stereo vision, calibrate your cameras:

```bash
# Install camera calibration tools
sudo apt install ros-humble-camera-calibration

# Run calibration (use checkerboard pattern)
ros2 run camera_calibration cameracalibrator \
    --size 8x6 \
    --square 0.024 \
    --approximate 0.01 \
    --no-service-check \
    right:=/stereo/right/image_raw \
    left:=/stereo/left/image_raw \
    right_camera:=/stereo/right \
    left_camera:=/stereo/left
```

Save calibration files and update the camera_info publishing in the node.

## Parameters

Edit [config/stereo_params.yaml](config/stereo_params.yaml) or pass as launch arguments:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `left_camera_id` | 0 | Left camera sensor ID or /dev/video index |
| `right_camera_id` | 1 | Right camera sensor ID or /dev/video index |
| `width` | 1280 | Image width in pixels |
| `height` | 720 | Image height in pixels |
| `fps` | 30 | Frame rate in Hz |
| `use_gstreamer` | true | Use GStreamer (CSI) vs V4L2 (USB) |
| `flip_method` | 0 | Rotation/flip (0-7) |
| `frame_id` | stereo_camera | TF frame ID |

## Common Resolutions for IMX219

- 3280 x 2464 @ 21 fps (full resolution)
- 1920 x 1080 @ 30 fps (1080p)
- 1640 x 1232 @ 30 fps
- 1280 x 720 @ 60 fps (720p)
- 640 x 480 @ 90 fps (VGA)

## Troubleshooting

### No Camera Detected

```bash
# Check if cameras are detected
ls /dev/video*

# Check camera capabilities
v4l2-ctl --list-devices

# For CSI cameras, check dmesg
dmesg | grep -i imx
```

### GStreamer Errors

If you see GStreamer errors with CSI cameras:
1. Verify cameras work with `nvgstcapture-1.0`
2. Check sensor-id matches your camera ports
3. Try lower resolution/fps
4. Ensure no other process is using cameras

### Low FPS / Performance Issues

1. **Reduce resolution**: Try 640x480 or 1280x720
2. **Lower FPS**: Set fps to 15 or 20
3. **Check CPU usage**: `htop`
4. **Use GStreamer**: Ensure `use_gstreamer: true` for CSI cameras
5. **Power mode**: Set Jetson to max performance
   ```bash
   sudo nvpmodel -m 0  # Max performance mode
   sudo jetson_clocks   # Max clock speeds
   ```

### USB Camera Not Working

1. Set `use_gstreamer: false`
2. Check camera permissions: `sudo chmod 666 /dev/video*`
3. Find correct video device: `v4l2-ctl --list-devices`
4. Test with: `ffplay /dev/video0`

### "Failed to open cameras!"

- Ensure no other process is using the cameras
- Check camera connections
- Verify camera IDs are correct
- Try running with sudo (not recommended for production)

## Integration with Other Packages

### With depth perception:
```bash
sudo apt install ros-humble-stereo-image-proc
ros2 run stereo_image_proc stereo_image_proc \
    left/image_raw:=/stereo/left/image_raw \
    right/image_raw:=/stereo/right/image_raw
```

### With SLAM:
Connect to ORB-SLAM3, RTAB-Map, or other stereo SLAM systems

### With obstacle detection:
Use depth maps for obstacle avoidance in navigation

## Performance Tips for Jetson

1. **Enable maximum performance:**
   ```bash
   sudo nvpmodel -m 0
   sudo jetson_clocks
   ```

2. **Monitor resources:**
   ```bash
   tegrastats
   ```

3. **Reduce compression** for network transmission:
   ```bash
   ros2 run image_transport republish raw compressed \
       in:=/stereo/left/image_raw
   ```

## License

Apache-2.0
