# MQTT Bridge for ROS Mower

This package provides an MQTT bridge for the ROS Mower system, enabling remote monitoring and control via MQTT.

## Features

- **Publishes to MQTT:**
  - GPS position (`/gps/fix`)
  - IMU data (`/imu/data`)
  - Odometry (`/odom`)
  - Pose (`/pose`)
  - Battery data (`/mavros/battery`, `/voltage`, `/percent`)
  - Robot mode status (`/robot_mode`)
  - System status

- **Subscribes from MQTT:**
  - Velocity commands (`/cmd_vel`)
  - Custom commands

## Installation

The package uses `paho-mqtt` for MQTT communication. Install dependencies:

```bash
cd /mnt/nova_ssd/rosmowercompleate/src/mqtt_bridge
pip3 install -r requirements.txt
```

## Configuration

Edit `config/mqtt_params.yaml` to configure your MQTT broker:

```yaml
mqtt_bridge:
  ros__parameters:
    mqtt_broker: "your-broker-address"  # e.g., "10.0.212.119" or "mqtt.example.com"
    mqtt_port: 1883
    mqtt_username: ""  # Optional
    mqtt_password: ""  # Optional
    base_topic: "rosmower"
```

## Usage

### Launch with default configuration:

```bash
ros2 launch mqtt_bridge mqtt_bridge.launch.py
```

### Launch with custom broker:

```bash
ros2 launch mqtt_bridge mqtt_bridge.launch.py mqtt_broker:=10.0.212.119
```

### Launch with custom topic prefix:

```bash
ros2 launch mqtt_bridge mqtt_bridge.launch.py base_topic:=my_robot
```

## MQTT Topics

With default `base_topic: "rosmower"`:

### Published by Bridge (ROS → MQTT):
- `rosmower/gps/fix` - GPS position data
- `rosmower/imu/data` - IMU sensor data
- `rosmower/odom` - Odometry data
- `rosmower/pose` - Robot pose
- `rosmower/battery` - Full battery state (voltage, current, percentage, etc.)
- `rosmower/battery/voltage` - Battery voltage (V)
- `rosmower/battery/percent` - Battery percentage (0-100)
- `rosmower/mode` - Current robot mode (idle/charging/mowing/full)
- `rosmower/status` - Bridge status (every 5 seconds)

### Subscribed by Bridge (MQTT → ROS):
- `rosmower/cmd_vel` - Velocity commands
- `rosmower/command` - Custom commands

## Example MQTT Messages

### Send velocity command:
```json
{
  "linear": {"x": 0.5, "y": 0.0, "z": 0.0},
  "angular": {"x": 0.0, "y": 0.0, "z": 0.3}
}
```

Publish to: `rosmower/cmd_vel`

### Monitor GPS:
Subscribe to: `rosmower/gps/fix`

Receive:
```json
{
  "latitude": 42.3601,
  "longitude": -71.0589,
  "altitude": 10.5,
  "status": 0,
  "service": 1
}
```

### Monitor Battery:
Subscribe to: `rosmower/battery`

Receive:
```json
{
  "voltage": 24.5,
  "current": -2.3,
  "percentage": 85.5,
  "power_supply_status": 2,
  "present": true
}
```

Subscribe to: `rosmower/battery/percent`

Receive:
```json
{
  "percent": 85.5
}
```

### Monitor Robot Mode:
Subscribe to: `rosmower/mode`

Receive:
```json
{
  "mode": "mowing"
}
```

Possible modes: `idle`, `charging`, `mowing`, `full`

## Testing

### Using mosquitto_pub/sub:

```bash
# Subscribe to all rosmower topics
mosquitto_sub -h localhost -t 'rosmower/#' -v

# Publish velocity command
mosquitto_pub -h localhost -t 'rosmower/cmd_vel' -m '{"linear":{"x":0.1,"y":0,"z":0},"angular":{"x":0,"y":0,"z":0}}'
```

## Building

```bash
cd /mnt/nova_ssd/rosmowercompleate
colcon build --packages-select mqtt_bridge
source install/setup.bash
```
