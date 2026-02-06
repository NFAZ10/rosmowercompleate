# ICM20948 IMU Driver for ROS2

ROS2 driver package for the ICM20948 9-axis IMU sensor found on the Waveshare IMX219-83 Stereo Camera.

## Overview

This package provides a ROS2 driver for the ICM20948 IMU sensor, which includes:
- **Accelerometer**: 3-axis, ±2/±4/±8/±16g configurable range (default: ±2g)
- **Gyroscope**: 3-axis, ±250/±500/±1000/±2000°/s configurable range (default: ±250°/s)
- **Magnetometer**: 3-axis, ±4900µT range
- **Temperature sensor**: Built-in temperature measurement

## Hardware Setup

### Connections

Connect the ICM20948 sensor to your system via I2C:

| ICM20948 Pin | System Pin | Description |
|--------------|------------|-------------|
| SDA | GPIO 2 (Pin 3) | I2C Data |
| SCL | GPIO 3 (Pin 5) | I2C Clock |
| VCC | 3.3V | Power |
| GND | GND | Ground |

### I2C Configuration

1. Enable I2C on your system (for Raspberry Pi/Jetson):
```bash
sudo raspi-config
# Navigate to: Interface Options -> I2C -> Enable
```

2. Verify I2C device is detected:
```bash
sudo i2cdetect -y 1
```

You should see address `0x68` in the output.

### Permissions

Add your user to the i2c group to access I2C without sudo:
```bash
sudo usermod -a -G i2c $USER
sudo reboot
```

## Installation

### Dependencies

Install required Python packages:
```bash
pip3 install smbus2
```

### Build

```bash
cd ~/ros2_ws
colcon build --packages-select icm20948_imu_driver
source install/setup.bash
```

## Usage

### Launch IMU Node

Basic launch:
```bash
ros2 launch icm20948_imu_driver icm20948.launch.py
```

With custom parameters:
```bash
ros2 launch icm20948_imu_driver icm20948.launch.py \
    i2c_bus:=1 \
    i2c_address:=0x68 \
    frame_id:=imu_link \
    publish_rate:=100.0
```

### Launch Stereo Camera with IMU

To launch both the stereo cameras and IMU together:
```bash
ros2 launch icm20948_imu_driver stereo_camera_with_imu.launch.py
```

### Run Node Directly

```bash
ros2 run icm20948_imu_driver icm20948_node
```

## Published Topics

| Topic | Type | Description |
|-------|------|-------------|
| `/imu/data_raw` | `sensor_msgs/Imu` | Raw IMU data (accel + gyro) |
| `/imu/mag` | `sensor_msgs/MagneticField` | Magnetometer data |
| `/imu/temperature` | `sensor_msgs/Temperature` | Temperature data |

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `i2c_bus` | int | 1 | I2C bus number |
| `i2c_address` | int | 0x68 | I2C address of ICM20948 |
| `frame_id` | string | "imu_link" | TF frame ID for messages |
| `publish_rate` | double | 100.0 | Publishing rate in Hz |
| `publish_temperature` | bool | true | Enable temperature publishing |
| `publish_magnetometer` | bool | true | Enable magnetometer publishing |

## Message Details

### IMU Message (`sensor_msgs/Imu`)

- **linear_acceleration**: Acceleration in m/s² (x, y, z)
- **angular_velocity**: Angular velocity in rad/s (x, y, z)
- **orientation**: Not computed (set to zeros, covariance[0] = -1)
- **covariances**: Diagonal covariance matrices provided

### MagneticField Message (`sensor_msgs/MagneticField`)

- **magnetic_field**: Magnetic field in Tesla (x, y, z)
- **magnetic_field_covariance**: Diagonal covariance matrix

### Temperature Message (`sensor_msgs/Temperature`)

- **temperature**: Temperature in Celsius
- **variance**: Temperature variance

## Calibration

For better accuracy, you should calibrate your IMU:

### Magnetometer Calibration

1. Collect data while rotating the sensor in all directions:
```bash
ros2 topic echo /imu/mag > mag_data.txt
```

2. Use calibration tools like [imu_utils](https://github.com/gaowenliang/imu_utils) or custom calibration scripts.

### Accelerometer/Gyroscope Calibration

Consider using packages like:
- [imu_calib](https://github.com/kyle-github/imu_calib)
- [imu_utils](https://github.com/gaowenliang/imu_utils)

## Troubleshooting

### I2C Communication Issues

1. **Device not detected**:
   - Check wiring connections
   - Verify I2C is enabled: `ls /dev/i2c*`
   - Run: `sudo i2cdetect -y 1`

2. **Permission denied**:
   - Add user to i2c group: `sudo usermod -a -G i2c $USER`
   - Reboot or re-login

3. **Clock stretching issues**:
   - On Raspberry Pi, add to `/boot/config.txt`:
     ```
     dtparam=i2c_arm_baudrate=50000
     ```

### Node Startup Issues

1. **Import errors**:
   - Ensure smbus2 is installed: `pip3 install smbus2`
   - Source workspace: `source install/setup.bash`

2. **Initialization failed**:
   - Check WHO_AM_I register value (should be 0xEA)
   - Verify I2C address is correct (default: 0x68)

## Sensor Specifications

| Specification | Value |
|--------------|-------|
| Accelerometer Range | ±2/±4/±8/±16g |
| Gyroscope Range | ±250/±500/±1000/±2000°/s |
| Magnetometer Range | ±4900µT |
| Resolution | 16-bit |
| Operating Voltage | 3.3V |
| Operating Current | Accel: 68.9µA, Gyro: 1.23mA, Mag: 90µA |
| Operating Temperature | 0-60°C |

## Integration with Stereo Camera

This IMU is mounted on the Waveshare IMX219-83 Stereo Camera module. For SLAM or visual-inertial odometry applications, you can fuse the IMU data with the stereo camera data using packages like:

- [rtabmap_ros](https://github.com/introlab/rtabmap_ros) - RGB-D and Stereo SLAM
- [ORB-SLAM3](https://github.com/UZ-SLAMLab/ORB_SLAM3) - Visual-Inertial SLAM
- [VINS-Fusion](https://github.com/HKUST-Aerial-Robotics/VINS-Fusion) - Visual-Inertial Odometry

## License

Apache-2.0

## References

- [ICM20948 Datasheet](https://invensense.tdk.com/products/motion-tracking/9-axis/icm-20948/)
- [Waveshare IMX219-83 Wiki](https://www.waveshare.com/wiki/IMX219-83_Stereo_Camera)
- [ROS2 sensor_msgs Documentation](https://docs.ros2.org/latest/api/sensor_msgs/)

## Author

Created for use with the Waveshare IMX219-83 Stereo Camera module.

## Support

For issues and questions, please refer to the Waveshare wiki or create an issue in the repository.
