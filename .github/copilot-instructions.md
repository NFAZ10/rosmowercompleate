# Copilot Instructions for rosmower

## Overview
A ROS 2-based autonomous mower robot platform integrating motor control, GPS/RTK, LIDAR, cameras, and IMU. Modular architecture with each subsystem (motors, sensors, navigation) as independent ROS 2 nodes orchestrated via launch files. Supports both native builds and Docker deployment on x86_64/ARM64 architectures.

## Architecture & Key Packages

**Core Packages** (in `src/`):
- **rosmower**: Main orchestration—launch files (`rosmower/launch/`), Python node scripts (`rosmower/scripts/`), and robot description (URDF/SDF in `description/` and `worlds/`).
  - `hoverboard_bridge_node.py`: Motor controller interface via serial; handles PWM commands, publishes `JointState` and `Odometry`, computes kinematics from encoders.
  - `tof_guard.py`, `vl53_bridge.py`: Time-of-flight sensor guardrails for collision detection.
  - `lidar_scan_guard.py`: LIDAR safety filtering.
  - `imu_bridge.py`: IMU integration for orientation telemetry.
  - `battery_splitter.py`: Battery monitoring from MAVROS.
  
- **gps_rtk**: UART-based GPS/RTK driver targeting Raspberry Pi GPIO header (pins 8/10 → `/dev/ttyAMA0`). Publishes `sensor_msgs/NavSatFix` and `geometry_msgs/TwistStamped`. Requires `enable_uart=1` in `/boot/config.txt`.

- **icm20948_imu_driver**: I2C IMU driver (address `0x68` default) for roll/pitch/yaw fusion.

- **sllidar_ros2**: LIDAR (SLAMTEC RPlidar) integration for SLAM/obstacle avoidance.

- **stereo_camera_viewer**: Multi-camera (USB/stereo) integration and visualization.

- **diffdrive_arduino**: Legacy Arduino motor interface (marked `COLCON_IGNORE`—kept for reference).

- **serial**: Cross-platform serial communication library used by multiple nodes.

**Data Flow**: Sensor/motor nodes → ROS 2 topics → Nav2 stack (localization, path planning, costmap). Example: `hoverboard_bridge_node` subscribes to `/cmd_vel` (Twist), publishes odometry; GPS publishes global position; LIDAR feeds Nav2 costmap.

## Web Control Interface

**Web Server** (`web_server.py`):
- Flask-based HTTP server running on port 8080
- Serves control interface and system status monitoring
- Managed via systemd service: `rosmower-web.service`
- Start/stop: `sudo systemctl start/stop/restart rosmower-web.service`

**Control Page** (`src/rosmower/web/mode_control.html`):
- Main robot control interface at `http://<robot-ip>:8080/`
- **Phone-style status bar** (top of page):
  - 📡 GPS Status: Displays fix quality (No GPS, 2D/3D Fix, RTK Float, RTK Fix)
  - ⏰ Time Display: Current time (HH:MM)
  - 🔋 Battery Indicator: Visual battery level with percentage (green >40%, yellow 20-40%, red flashing <20%)
- **ROS Bridge Connection**: Uses roslib.js to connect to rosbridge_websocket (default: `ws://10.31.18.195:9090`)
- **Mode Control Buttons**: Set robot operating modes via `/robot_mode_cmd` topic (idle, charging, mowing, full)
- **Mission Controls** (🌿 section below mode buttons):
  - 🚀 **Launch Mission**: Calls `/api/command/mission` → runs `openmower_mission.launch.py` inside the robot container
  - ▶️ **Start Mowing**: Publishes `START` to `/mission/command`
  - 🏠 **Return to Dock**: Publishes `RETURN_TO_DOCK` to `/mission/command`
  - 🆘 **Emergency Dock**: Publishes `EMERGENCY_DOCK` to `/mission/command`
  - 🔋 **Mark Charged**: Publishes `BATTERY_CHARGED` to `/mission/command`
  - 🗺️ **Zone Manager**: Opens `/zones` page in a new tab
  - Live status panel: shows Mission State (color-coded), Active Zone, and Progress
- **System Controls**: Launch, status, GPS, bridge, restart, stop Docker container
- **Real-time Updates**: Subscribes to `/robot_mode`, `/battery_state`, `/gps/fix`, `/mission/state`, `/mission/active_zone`, `/mission/progress` topics for live status

**Status Monitor Page** (`src/rosmower/web/status.html`):
- Node status dashboard at `http://<robot-ip>:8080/status`
- Opens in new tab (preserves rosbridge connection on control page)
- Displays all running ROS 2 nodes and topics
- Auto-refreshes every 5 seconds
- Shows Docker container status (running/stopped)
- "Start Container" button appears when container is stopped
- Color-coded status indicators (green pulse = running, red = stopped)

**API Endpoints** (REST):
- `/api/status`: Container and rosbridge status
- `/api/ros/nodes`: List all running ROS nodes and topics (reads from Docker container)
- `/api/command/<cmd>`: Execute docker-helper.sh commands (launch, bridge, gps, stat, stop, restart, **mission**)
- `/api/docker/start|stop|restart`: Docker container lifecycle management
- `/api/process/<name>/status`: Background process status (for launch/bridge commands)

**Key Integration Points**:
- **ROS Topics**: Status bar subscribes to `/battery_state` (sensor_msgs/BatteryState), `/gps/fix` (sensor_msgs/NavSatFix), `/robot_mode` (std_msgs/String)
- **Docker**: All ROS commands execute inside `rosmower_robot` container via `docker exec`
- **rosbridge_websocket**: Required for web interface to communicate with ROS (run via `docker-helper.sh bridge`)

**Setup/Deployment**:
```bash
./install-web-server.sh    # Install systemd service
sudo systemctl enable rosmower-web.service
sudo systemctl start rosmower-web.service
# Access at http://<robot-ip>:8080 or http://localhost:8080
```

## Build & Development Workflows

### Native Build (Linux/WSL)
```bash
colcon build --symlink-install              # Full build with symlinks (for live editing)
colcon build --packages-select rosmower     # Build single package
source install/setup.bash                   # Source environment (must do before launching)
ros2 launch rosmower launch_robot.launch.py # Launch full stack
```

### Docker Build & Run (Recommended)
```bash
./build-docker.sh [slim|desktop]  # Auto-detects architecture (x86_64 vs ARM64), builds Dockerfile or Dockerfile.arm64
./docker-helper.sh run             # Runs container with --privileged --network host for hardware/ROS 2 DDS
./docker-helper.sh dev             # Development shell with mounted workspace
```
Docker key setup: Maps `/dev` and `/run/udev:ro` for hardware; `ROS_DOMAIN_ID=0`; uses `ros:humble` base image; runs as root for device access simplicity.

### Setup & Dependencies
```bash
./setup-dev.sh  # Installs ROS 2 Humble, colcon, rosdep, build tools
```

## Critical Conventions & Patterns

### Launch Files Are Entrypoints (Not Scripts)
All robot startup via Python launch files (NOT shell scripts or manual node invocation). Launch files compose related nodes:
- **`launch_robot.launch.py`**: Main bringup combining motors, IMU, GPS, LIDAR, cameras, state publisher.
- **`navigation_launch.py`**: Nav2 stack (localization, path planning, amcl).
- **`rsp.launch.py`**: Robot state publisher for URDF/transform publishing.
- **`hoverboard_bridge_only.launch.py`**: Motor control standalone (useful for testing).

Launch args override defaults: `ros2 launch rosmower launch_robot.launch.py port:=/dev/ttyUSB0 max_lin:=0.5`.

### ROS 2 Node Pattern (Python in `rosmower/scripts/`)
Every sensor/motor node follows this structure:
1. **Inherit `rclpy.Node`** and define `__init__`:
   ```python
   class MyNode(Node):
       def __init__(self):
           super().__init__('my_node')
           # Declare all parameters with defaults
           self.declare_parameter('device_port', '/dev/ttyUSB0')
           self.declare_parameter('update_rate', 50.0)  # Hz
   ```
2. **Create publishers/subscribers/services** in `__init__`.
3. **Implement main loop** via `create_timer()` or `spin()`.
4. **Use parameters** from launch files: `self.get_parameter('device_port').get_parameter_value().string_value`.

Example: `hoverboard_bridge_node.py` declares `port`, `wheel_radius`, `max_pwm`; publishes `JointState`/`Odometry`; subscribes to `cmd_vel` (Twist).

### Device Path Parameterization
All serial/sensor device paths exposed as launch arguments:
- **Hoverboard motor controller**: `/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0` (launch arg: `port`)
- **GPS UART**: `/dev/ttyAMA0` on Raspberry Pi (must enable GPIO UART in `/boot/config.txt`)
- **IMU I2C**: Address `0x68` (launch arg: `i2c_addr` if configurable)
- **LIDAR**: `/dev/ttyUSB0` or similar (launch arg: `lidar_port`)

Use `ros2 launch ... --show-args` to see all available parameters.

### Hardcoded Assumptions to Check/Update
- **Wheel radius/separation**: Defaults in `hoverboard_bridge_node.py` (search `wheel_radius=0.16`, `wheel_separation=0.52`). Must match physical robot for accurate odometry.
- **Robot description (URDF)**: Check `description/` for link/joint definitions; used by state publisher and Nav2.
- **Frame IDs**: Typically `odom` (global) → `base_link` (robot center) → sensor frames. Check launch files for `base_frame_id`, `odom_frame_id`.
- **Max PWM/velocity scales**: `max_pwm=255`, `max_lin=1.0 m/s`, `max_ang=2.0 rad/s` in hoverboard (launch args to override).

### Package Disabling Convention
Use `COLCON_IGNORE` file in package root to skip building (e.g., `diffdrive_arduino` is disabled). Useful for optional or WIP packages.

## CLI Status Monitor (`status.py`)

**Terminal-based real-time status dashboard** for monitoring all ROS 2 topics and system state:
- **Box-style UI**: Each topic displayed in its own colored box with title and age indicator
- **Auto-hide empty topics**: Only shows topics with active data
- **Color-coded indicators**:
  - Battery voltage: **Green** (≥26.5V), **Red** (<26.5V)
  - Node status: **Green** (ACTIVE), **Red** (OFFLINE)
  - Features: **Green** (enabled), **Dimmed** (disabled)
- **Monitors by default**:
  - Node Status: bridge, camera, MAVROS, motor_controller, sllidar, gps_rtk, imu
  - System Features: Motors, Sensors, GPS, LiDAR, Camera enable states
  - Robot Mode: Current operating mode (idle/charging/mowing/full)
  - Battery: Voltage, percentage, current from `/battery_state`
  - GPS/RTK: Lat/lon, altitude, RTK status, accuracy from `/gps/fix`
  - IMU: Roll/pitch/yaw, angular velocity, linear acceleration from `/mavros/imu/data`

**Usage**:
```bash
./status.py                          # Run with defaults (2 Hz refresh)
./status.py --hz 5                   # Faster refresh rate
./status.py --yaml sources.yaml      # Load custom topic config
./status.py --add "MyTopic:/my_topic:std_msgs/msg/Float32:value=data"
./status.py --once                   # Print once and exit
```

**Customization**: Extend with `--add` for inline topics or `--yaml` for YAML config files. Supports nested paths (`orientation.x`), computed fields (`c:yaw_deg`), and custom formatting.

## Common Development Tasks

| Task | How-To |
|------|--------|
| **Run autonomous mowing mission** | Web UI: click 🚀 Launch Mission then ▶️ Start Mowing; or CLI: `./docker-helper.sh mission -d` then publish `START` to `/mission/command` |
| **Add new sensor node** | Copy `rosmower/scripts/tof_guard.py` template; declare params, publish sensor_msgs, add launch file entry |
| **Debug node communication** | `ros2 topic list`, `ros2 topic echo /topic_name`, `ros2 node info /node_name`, `ros2 topic hz /topic_name` |
| **Monitor system status** | Run `./status.py` for live terminal dashboard with color-coded status (battery, GPS, IMU, nodes) |
| **Change motor behavior** | Edit velocity/PWM kinematics in `hoverboard_bridge_node.py` or override launch args (`max_lin`, `wheel_radius`) |
| **Configure device paths** | Edit launch file (e.g., `launch_robot.launch.py`) or pass `arg:=value` on command line |
| **Test single component** | `ros2 launch rosmower hoverboard_bridge_only.launch.py` (motor-only), `ros2 launch rosmower rplidar.launch.py` (LIDAR-only) |
| **Check ROS 2 middleware** | Middleware config in `cyclonedds.xml` (CycloneDDS); used by all ROS 2 communication |
| **Run Zenoh bridge** | Inside container: `zenoh-bridge-dds` to bridge ROS 2 DDS topics to Zenoh protocol for low-bandwidth/multi-robot scenarios |
| **Access web interface** | Navigate to `http://<robot-ip>:8080` (control) or `/status` (monitoring); ensure rosbridge running: `./docker-helper.sh bridge` |
| **Restart web server** | `sudo systemctl restart rosmower-web.service` (changes to `web_server.py` or HTML files require restart) |
| **Add web API endpoint** | Edit `web_server.py`, add `@app.route()` decorator, restart service |

## External Integrations & Dependencies

- **ROS 2 Humble**: Core framework; all packages target humble (foxy/rolling support in individual READMEs).
- **Nav2 Stack**: Autonomous navigation—expects odometry (`odom` frame) and LIDAR input; configured in `navigation_launch.py`.
- **MAVROS**: FCU/PX4 integration (pre-installed in Docker, currently unused—see `test_mavros/` and `battery_splitter.py` for reference).
- **Zenoh**: High-performance pub/sub protocol for distributed systems; installed in Docker containers.
  - **`zenohd`**: Zenoh router/daemon for creating mesh networks
  - **`zenoh-bridge-dds`**: DDS bridge for ROS 2 integration—enables ROS 2 topics over Zenoh protocol
  - Use case: Low-bandwidth or unreliable network environments, multi-robot systems
  - Commands available in container: `zenohd`, `zenoh-bridge-dds`
- **Hardware Drivers**:
  - **Arduino**: Legacy motor control (diffdrive_arduino, currently disabled).
  - **SLAMTEC RPlidar**: Via `sllidar_ros2` package.
  - **GPS/RTK modules**: Custom UART driver in `gps_rtk/`.
  - **IMU (ICM-20948)**: Custom I2C driver in `icm20948_imu_driver/`.

## Debugging Checklist

1. **Build fails**: Check `COLCON_IGNORE` in affected package; ensure ROS 2 is sourced; run `rosdep install --from-paths src --ignore-src -r -y`.
2. **Node won't start**: Device path missing? `ls -la /dev/ttyXXX` or `/dev/serial/by-id/`. Check launch args with `ros2 launch ... --show-args`.
3. **No motor movement**: Verify `hoverboard_bridge_node` running (`ros2 node list`). Test command with `ros2 topic pub /cmd_vel geometry_msgs/Twist "{linear: {x: 0.1}}"`.
4. **GPS not publishing**: Verify GPIO UART enabled (`grep enable_uart /boot/config.txt` on RPi). Check serial port permissions: `sudo chmod 666 /dev/ttyAMA0`.
5. **TF errors**: Check `rsp.launch.py` is running; verify URDF exists in `description/`.
6. **Build times**: Use `colcon build --parallel-workers $(nproc)` or Docker for faster, isolated builds.
7. **Web interface not connecting**: Verify rosbridge running (`docker exec rosmower_robot ros2 node list | grep rosbridge`); check firewall allows port 9090; confirm websocket URL matches robot IP.
8. **Status page shows "Container not running"**: Start container with `docker start rosmower_robot` or use "Start Container" button in web UI.

## References & Key Files

- **Launch files**: [rosmower/launch/](src/rosmower/launch) (all orchestration entry points)
- **Node scripts**: [rosmower/scripts/](src/rosmower/scripts) (sensor/motor implementations)
- **Robot description**: [rosmower/description/](src/rosmower/description) (URDF/SDF)
- **Package docs**: Each `src/<package>/README.md` for hardware-specific setup
- **Web interface**: [web_server.py](web_server.py) (Flask server), [src/rosmower/web/](src/rosmower/web) (HTML/CSS/JS frontend)
- **CLI status monitor**: [status.py](status.py) (terminal dashboard with color-coded boxes)
- **Docker setup**: [DOCKER_README.md](DOCKER_README.md), [docker-helper.sh](docker-helper.sh)
- **Configuration**: [sources.yaml](sources.yaml) (telemetry config for status.py), [cyclonedds.xml](cyclonedds.xml) (ROS 2 DDS)

---

**Need help?** Check launch files for examples of parameter passing. Search scripts for `declare_parameter` to see all configurable values. Ask clarifying questions about expected vs. actual node behavior or device connectivity.
