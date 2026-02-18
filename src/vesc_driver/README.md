# VESC Driver for ROS 2 Humble

ROS 2 C++ driver for VESC motor controllers with CAN bus support for differential drive robots.

## Features

- **Dual VESC Control**: Controls two VESC 6.x motor controllers over USB + CAN bus
- **Differential Drive**: Converts `geometry_msgs/Twist` to left/right wheel RPM
- **Joint State Publishing**: Publishes `sensor_msgs/JointState` from VESC ERPM feedback
- **Odometry**: Optional odometry publishing from wheel encoders
- **CAN Bus Support**: Primary VESC via USB, secondary via CAN forwarding
- **Thread-Safe**: Async serial communication with mutex protection
- **Configurable**: Wheel geometry, motor pole pairs, and safety limits via parameters

## Hardware Setup

### Typical Configuration
- **2× VESC 6.7** motor controllers (based on VESC 6.6)
- **2× 300W hoverboard BLDC motors** with Hall sensors
- **24V LiFePO4** battery system
- **CAN bus** connection between VESCs
- **USB serial** from Jetson to VESC ID 0

### Wiring
1. VESC ID 0: Connected to Jetson via USB (e.g., `/dev/ttyACM0`)
2. VESC ID 1: Connected to VESC ID 0 via CAN bus (CAN-H, CAN-L, GND)
3. Configure VESC IDs using VESC Tool

## Dependencies

- ROS 2 Humble
- `rclcpp`
- `geometry_msgs`
- `sensor_msgs`
- `nav_msgs`
- `tf2`

## Building

```bash
cd ~/rosmower_ws
colcon build --packages-select vesc_driver --symlink-install
source install/setup.bash
```

## Usage

### Basic Launch
```bash
ros2 launch vesc_driver vesc_driver.launch.py
```

### With Custom Parameters
```bash
ros2 launch vesc_driver vesc_driver.launch.py \
  serial_port:=/dev/ttyACM0 \
  wheel_radius:=0.0875 \
  wheel_separation:=0.52 \
  pole_pairs:=15 \
  left_vesc_can_id:=0 \
  right_vesc_can_id:=1
```

### Test Drive
```bash
# Publish cmd_vel to drive forward
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.2}, angular: {z: 0.0}}"

# Rotate in place
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.0}, angular: {z: 0.5}}"
```

## Topics

### Subscribed
- `/cmd_vel` (`geometry_msgs/msg/Twist`) - Velocity commands

### Published
- `joint_states` (`sensor_msgs/msg/JointState`) - Wheel joint states (position, velocity, effort)
- `odom` (`nav_msgs/msg/Odometry`) - Odometry from wheel encoders (optional)

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `serial_port` | string | `/dev/ttyACM0` | Serial port for VESC ID 0 |
| `baudrate` | int | `115200` | Serial baud rate |
| `wheel_radius` | double | `0.0875` | Wheel radius (m) |
| `wheel_separation` | double | `0.52` | Distance between wheels (m) |
| `pole_pairs` | int | `15` | Motor pole pairs |
| `left_vesc_can_id` | int | `0` | Left VESC CAN ID |
| `right_vesc_can_id` | int | `1` | Right VESC CAN ID |
| `max_rpm` | int | `3000` | Max ERPM safety limit |
| `control_rate` | double | `50.0` | Control loop rate (Hz) |
| `telemetry_rate` | double | `10.0` | Telemetry request rate (Hz) |
| `publish_odom` | bool | `true` | Enable odometry publishing |
| `odom_frame_id` | string | `odom` | Odometry frame ID |
| `base_frame_id` | string | `base_link` | Base frame ID |

## Differential Drive Kinematics

The node converts linear (`v`) and angular (`w`) velocities to wheel velocities:

```
v_left = v - (w × L / 2)
v_right = v + (w × L / 2)
```

Where `L` is `wheel_separation`.

Wheel angular velocity:
```
ω_wheel = v_wheel / wheel_radius
```

RPM conversion:
```
RPM = ω_wheel × 60 / (2π)
ERPM = RPM × pole_pairs
```

## VESC Configuration

Configure your VESCs using VESC Tool:

1. **Motor Detection**: Run motor detection wizard for both VESCs
2. **CAN IDs**: Set VESC IDs (0 for USB-connected, 1 for CAN-connected)
3. **CAN Bus**: Enable CAN forwarding on VESC ID 0
4. **Current Limits**: Set appropriate current limits for 300W motors (~12A peak)
5. **RPM Limits**: Configure max ERPM based on your motor specs
6. **Hall Sensors**: Ensure Hall sensors are properly detected

## Safety Features

- **Command Timeout**: Motors stop if no cmd_vel received for 500ms
- **RPM Limiting**: Enforces max ERPM to prevent motor damage
- **Thread-Safe**: Mutex-protected state access
- **CRC Validation**: Verifies VESC packet integrity

## Troubleshooting

### No Serial Connection
```bash
# Check USB connection
ls -l /dev/ttyACM*

# Add user to dialout group
sudo usermod -aG dialout $USER

# Set permissions
sudo chmod 666 /dev/ttyACM0
```

### Motors Not Responding
- Verify VESC IDs match configuration
- Check CAN bus wiring (CAN-H, CAN-L, GND)
- Ensure VESCs are powered (24V connected)
- Verify motor detection completed in VESC Tool
- Check fault codes in VESC telemetry

### Erratic Movement
- Calibrate wheel radius and separation
- Verify motor pole pairs (check VESC Tool)
- Check motor direction (swap two motor wires if reversed)
- Ensure Hall sensors properly configured

### High CPU Usage
- Reduce `control_rate` (e.g., to 20 Hz)
- Reduce `telemetry_rate` (e.g., to 5 Hz)

## Integration with Nav2

This driver publishes `joint_states` and `odom` compatible with Nav2:

```bash
# Launch VESC driver
ros2 launch vesc_driver vesc_driver.launch.py

# Launch Nav2 (example)
ros2 launch nav2_bringup navigation_launch.py
```

Ensure your robot URDF includes wheel joints matching the joint names:
- `left_wheel_joint`
- `right_wheel_joint`

## Advanced: Multiple VESC Pairs

For robots with >2 motors, extend the driver to support multiple CAN IDs:

```cpp
// Example: 4-wheel drive
vesc_->setRPMCAN(0, front_left_erpm);
vesc_->setRPMCAN(1, front_right_erpm);
vesc_->setRPMCAN(2, rear_left_erpm);
vesc_->setRPMCAN(3, rear_right_erpm);
```

## License

Apache 2.0

## Author

Autonomous Mower Team

## References

- [VESC Project](https://vesc-project.com/)
- [VESC Serial Protocol](https://github.com/vedderb/bldc/blob/master/comm_protocol.txt)
- [ROS 2 Navigation](https://navigation.ros.org/)
