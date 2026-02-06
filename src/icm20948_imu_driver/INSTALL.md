# Installation and Quick Start Guide

## Prerequisites

### System Requirements
- ROS2 (Humble/Foxy or later)
- Python 3.8+
- I2C enabled on your system
- Waveshare IMX219-83 Stereo Camera with ICM20948 IMU

### Install Dependencies

```bash
# Install Python I2C library
pip3 install smbus2

# Install ROS2 dependencies (if not already installed)
sudo apt-get update
sudo apt-get install ros-${ROS_DISTRO}-sensor-msgs ros-${ROS_DISTRO}-geometry-msgs
```

## Hardware Setup

### Enable I2C

**For Raspberry Pi:**
```bash
sudo raspi-config
# Navigate to: Interface Options -> I2C -> Enable
sudo reboot
```

**For Jetson Nano/Xavier:**
```bash
# I2C is usually enabled by default
# Verify with:
ls /dev/i2c*
```

### I2C Permissions

```bash
# Add user to i2c group
sudo usermod -a -G i2c $USER

# Reboot to apply changes
sudo reboot
```

### Verify Hardware Connection

```bash
# Install i2c-tools if not present
sudo apt-get install i2c-tools

# Scan I2C bus (bus 1 is typical)
sudo i2cdetect -y 1
```

You should see device at address `0x68`:
```
     0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f
00:          -- -- -- -- -- -- -- -- -- -- -- -- -- 
10: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
20: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
30: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
40: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
50: -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- -- 
60: -- -- -- -- -- -- -- -- 68 -- -- -- -- -- -- -- 
70: -- -- -- -- -- -- -- --
```

## Installation

### 1. Clone or Copy Package

```bash
cd ~/isaac_ros-dev/src
# Package should be at: isaac_ros-dev/src/icm20948_imu_driver
```

### 2. Build Package

```bash
cd ~/isaac_ros-dev
colcon build --packages-select icm20948_imu_driver
source install/setup.bash
```

### 3. Test Hardware (Before ROS2)

```bash
# Run hardware test script
python3 ~/isaac_ros-dev/src/icm20948_imu_driver/scripts/test_imu.py
```

Expected output:
```
============================================================
ICM20948 IMU Test
============================================================

1. Initializing sensor on I2C bus 1, address 0x68...
✓ Sensor initialized successfully!

2. Reading sensor data (10 samples)...
------------------------------------------------------------
Sample   Accel (m/s²)                   Gyro (rad/s)                   Temp (°C) 
------------------------------------------------------------
1        (  0.12,  -0.05,   9.81)      ( 0.002, -0.001,  0.000)       23.45
...
```

## Quick Start

### Launch IMU Node

**Option 1: Basic launch**
```bash
ros2 launch icm20948_imu_driver icm20948.launch.py
```

**Option 2: With custom parameters**
```bash
ros2 launch icm20948_imu_driver icm20948.launch.py \
    i2c_bus:=1 \
    publish_rate:=100.0 \
    frame_id:=imu_link
```

**Option 3: Run node directly**
```bash
ros2 run icm20948_imu_driver icm20948_node
```

### View IMU Data

**Using IMU viewer (recommended):**
```bash
# Terminal 1: Launch IMU node
ros2 launch icm20948_imu_driver icm20948.launch.py

# Terminal 2: Run viewer
python3 ~/isaac_ros-dev/src/icm20948_imu_driver/scripts/imu_viewer.py
```

**Using ROS2 topic echo:**
```bash
# View IMU data
ros2 topic echo /imu/data_raw

# View magnetometer data
ros2 topic echo /imu/mag

# View temperature
ros2 topic echo /imu/temperature
```

**List all topics:**
```bash
ros2 topic list
```

### Launch with Stereo Camera

```bash
ros2 launch icm20948_imu_driver stereo_camera_with_imu.launch.py
```

This launches both stereo cameras and the IMU simultaneously.

## Verification

### Check Node is Running

```bash
ros2 node list
# Should show: /icm20948_imu
```

### Check Topics

```bash
ros2 topic list
# Should show:
# /imu/data_raw
# /imu/mag
# /imu/temperature
```

### Check Publishing Rate

```bash
ros2 topic hz /imu/data_raw
# Should show approximately 100 Hz
```

### Visualize in RViz2

```bash
# Launch RViz2
rviz2

# Add -> By topic -> /imu/data_raw -> Imu
# Set Fixed Frame to: imu_link
```

## Troubleshooting

### Issue: "Failed to initialize ICM20948"

**Solutions:**
1. Check I2C wiring (SDA, SCL, VCC, GND)
2. Verify I2C is enabled: `ls /dev/i2c*`
3. Check device is detected: `sudo i2cdetect -y 1`
4. Verify WHO_AM_I register: Should return 0xEA

### Issue: "Permission denied" when accessing I2C

**Solutions:**
1. Add user to i2c group: `sudo usermod -a -G i2c $USER`
2. Reboot system
3. Check permissions: `ls -l /dev/i2c-1`

### Issue: "No module named 'smbus2'"

**Solution:**
```bash
pip3 install smbus2
```

### Issue: Magnetometer returns zeros

**Solutions:**
1. Magnetometer initialization can be finicky
2. Power cycle the sensor
3. Keep the sensor away from magnetic interference
4. Check I2C master mode is enabled

### Issue: Data seems noisy or incorrect

**Solutions:**
1. Ensure sensor is stable during initialization
2. Apply calibration (see README.md)
3. Check for loose connections
4. Reduce I2C bus speed if experiencing communication errors

## Next Steps

1. **Calibration**: Calibrate your IMU for better accuracy
2. **Integration**: Integrate with your stereo camera for visual-inertial odometry
3. **SLAM**: Use with SLAM packages like rtabmap_ros or ORB-SLAM3
4. **Filtering**: Apply sensor fusion (e.g., Madgwick, Mahony filters)

## Additional Resources

- [Full README](README.md) - Detailed documentation
- [ICM20948 Datasheet](https://invensense.tdk.com/products/motion-tracking/9-axis/icm-20948/)
- [Waveshare Wiki](https://www.waveshare.com/wiki/IMX219-83_Stereo_Camera)
- [ROS2 Documentation](https://docs.ros.org/)
