# ROS Mower Mode Control System

This system allows you to switch between different operational modes at runtime without restarting the robot.

## Modes

### 💤 IDLE
- **Use case**: Low power standby mode
- **Active systems**: None
- **Best for**: When robot is parked and not charging

### 🔋 CHARGING
- **Use case**: Battery charging mode
- **Active systems**: Battery monitoring only
- **Best for**: When robot is on charging station

### 🌱 MOWING
- **Use case**: Full autonomous mowing operation
- **Active systems**: Motors, GPS, LIDAR, cameras, all sensors
- **Best for**: Active mowing tasks

### ⚡ FULL
- **Use case**: Maximum capability mode
- **Active systems**: Everything enabled
- **Best for**: Testing, debugging, development

## How to Use

### Web Interface (Recommended)

1. **Start the robot with rosbridge enabled** (default):
   ```bash
   ./docker-helper.sh launch
   ```

2. **Open the web interface** in your browser:
   - Open `src/rosmower/web/mode_control.html` in any web browser
   - Or access it from the installed location after building

3. **Connect to your robot**:
   - Default: `ws://localhost:9090` (if running on same machine)
   - Remote: `ws://ROBOT_IP:9090` (replace ROBOT_IP with your robot's IP)

4. **Click the mode button** you want to activate

### Command Line

Change mode using ROS 2 topic:
```bash
# Set to IDLE mode
ros2 topic pub /robot_mode_cmd std_msgs/String "data: 'idle'" --once

# Set to CHARGING mode
ros2 topic pub /robot_mode_cmd std_msgs/String "data: 'charging'" --once

# Set to MOWING mode
ros2 topic pub /robot_mode_cmd std_msgs/String "data: 'mowing'" --once

# Set to FULL mode
ros2 topic pub /robot_mode_cmd std_msgs/String "data: 'full'" --once
```

Check current mode:
```bash
ros2 topic echo /robot_mode
```

## Topics

- `/robot_mode_cmd` (std_msgs/String) - Publish here to change mode
- `/robot_mode` (std_msgs/String) - Current mode status (published at 1 Hz)
- `/enable_motors` (std_msgs/Bool) - Motor enable/disable
- `/enable_sensors` (std_msgs/Bool) - Sensor enable/disable
- `/enable_gps` (std_msgs/Bool) - GPS enable/disable
- `/enable_lidar` (std_msgs/Bool) - LIDAR enable/disable
- `/enable_camera` (std_msgs/Bool) - Camera enable/disable

## Configuration

Set the initial mode in the launch file:
```python
mode_manager_node = Node(
    package='rosmower',
    executable='mode_manager.py',
    name='mode_manager',
    output='screen',
    parameters=[{
        'initial_mode': 'idle'  # Change this: idle, charging, mowing, full
    }]
)
```

## Troubleshooting

**Web interface won't connect:**
- Check rosbridge is running: `ros2 node list | grep rosbridge`
- Verify port 9090 is accessible
- Check firewall settings

**Mode changes don't take effect:**
- Verify mode_manager is running: `ros2 node list | grep mode_manager`
- Check topic communication: `ros2 topic echo /robot_mode`
- Look for errors: `ros2 node info /mode_manager`

**Motors don't stop in IDLE mode:**
- The hoverboard_bridge_node should subscribe to `/enable_motors`
- Send manual stop: `ros2 service call /stop std_srvs/Trigger`
