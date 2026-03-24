# ROS2 Humble Rosmower Repository - Deep Inspection Report

**Repository Path:** `/mnt/nova_ssd/rosmowercompleate`
**Date:** March 2024

---

## 1. DIRECTORY STRUCTURE & PACKAGES

### Source Packages (src/)
Located at: `/mnt/nova_ssd/rosmowercompleate/src/`

| Package | Type | Purpose |
|---------|------|---------|
| **rosmower** | CMake | Main robot control package - core node launcher, scripts for motor control, sensors |
| **rosmower_msgs** | CMake | Custom ROS2 message/service definitions (zones, routes, missions) |
| **vesc_driver** | CMake | C++ driver for VESC motor controllers via CAN bus |
| **test_mavros** | Catkin | MAVROS test package with SITL integration |
| **gps_rtk** | Python | GPS/RTK driver for UART on 40-pin Jetson header |
| **icm20948_imu_driver** | Python | ICM20948 9-axis IMU driver for stereo camera module |
| **mqtt_bridge** | Python | MQTT bridge for Home Assistant telemetry |
| **openmower_mission** | Python | Mission execution and coverage path planning (boustrophedon) |
| **stereo_camera_viewer** | Python | Waveshare IMX219 stereo camera driver with hardware acceleration |
| **sllidar_ros2** | CMake | RPLidar C1 driver with motor control support |
| **serial** | CMake | Cross-platform serial library (RS-232) |
| **mqtt_bridge** | Python | MQTT integration |

### Top-Level Files & Directories
- **web_server.py** (1432 lines) - Flask web UI server for robot control
- **docker-compose.yml** - Main Docker orchestration (contains rosmower, rviz, dev services)
- **docker-compose-multi.yml** - Multi-zone variant with Zenoh networking
- **Dockerfile** & **Dockerfile.arm64** - Container images
- **mav.parm** - MAVLink parameter file for ArduPilot-compatible FCU
- **sources.yaml** - ROS2 telemetry topic mapping configuration
- **cyclonedds.xml** - DDS middleware configuration
- **routes/** - Route definition directory (YAML format)
- **zones/** - Recorded zone polygons storage
- **documentation/** - 80+ markdown files with architecture, guides, and quick-start docs

---

## 2. MAVROS INTEGRATION

### MAVROS Usage Summary
MAVROS (MAVLink to ROS bridge) is ACTIVELY USED for:
- Flight controller (FCU) communication via serial/USB
- Battery status monitoring
- IMU data relay
- GPS integration

### Key Files with MAVROS References
1. **Launch Files:**
   - `/src/rosmower/launch/launch_robot.launch.py` (lines 331-340) - Main MAVROS node launcher
   - `/src/rosmower/launch/mavros_usb_min.launch.py` - Minimal USB-only MAVROS setup
   - `/src/rosmower/launch/battery_splitter.launch.py` - Battery topic mapping

2. **Configuration:**
   - `/src/rosmower/config/mavros.yaml` - FCU URL template: `serial:///${DEV}:115200`
   - `/src/rosmower/config/ekf.yaml` - Uses MAVROS topics:
     - `imu0: /mavros/imu/data`
     - `gps0: /mavros/global_position/local`

3. **Python Nodes:**
   - `battery_splitter.py` - Subscribes to `/mavros/battery` (BatteryState)
   - `imu_bridge.py` - Bridges `/mavros/imu/data` → `/imu/data_raw`
   - `stabilitty.py` - Reads `/mavros/imu/data` for tilt control

4. **MQTT Bridge:**
   - `mqtt_bridge_node.py` - Maps `/mavros/battery` to MQTT for Home Assistant

### MAVROS Configuration Details
```yaml
fcu_url: "serial:///${DEV}:115200"
fcu_protocol: "v2.0"
```

**Serial Device:** 
- Default: `/dev/serial/by-id/usb-ArduPilot_SpeedyBeeF405WING_310037000850314E41313720-if00`
- Override at launch: `ros2 launch ... dev:=/dev/ttyACM0`

**Supported MAVLink Topics Published by MAVROS:**
- `/mavros/battery` - BatteryState (voltage, current, percentage)
- `/mavros/imu/data` - Imu (accelerometer, gyroscope, magnetometer)
- `/mavros/global_position/local` - NavSatFix (GPS lat/lon/alt)
- `/mavros/state` - State (mode, armed status)
- `/tf` - Transform frames (base_link → map)

---

## 3. SERVO/BLADE/MOTOR/PWM REFERENCES

### Motor Control Architecture

#### VESC Driver (Primary Motor Controller)
**File:** `/src/vesc_driver/src/vesc_driver_node.cpp`
- **Type:** Differential drive motor controller via CAN bus
- **Hardware:** Two VESC controllers (left ID=0 USB, right ID=5 CAN)
- **Interface:** CAN bus at 115200 baud over USB serial
- **Motor Specs:** Hoverboard motors, 15 pole pairs
- **Control Mode:** Duty cycle (0-100% PWM)

**Key Parameters:**
```cpp
left_vesc_can_id: 0 (USB-connected)
right_vesc_can_id: 5 (CAN bus)
pole_pairs: 15
max_lin: 1.0 m/s (maps to 100% duty cycle)
invert_left_motor: false
invert_right_motor: false
control_rate: 50.0 Hz
```

**Published Topics:**
- `joint_states` → `/wheel_joint_states` (effort = motor current)
- `odom` (if enabled) → wheel odometry from encoders

**Subscribed Topics:**
- `/cmd_vel_motors` (geometry_msgs/Twist) → PWM duty cycle

---

#### Hoverboard Bridge (Alternative Motor Interface)
**File:** `/src/rosmower/scripts/hoverboard_bridge_node.py`
- **Type:** Legacy Arduino-based motor interface via serial
- **Protocol:** Text-based serial commands (VEL, ARM, STOP, BLADE, DIRINV, BRAKE)
- **Hardware:** Arduino with hoverboard motor controllers
- **PWM Range:** 0-255 (or -255 to 255 for bidirectional)

**Serial Commands:**
```
VEL <left_pwm> <right_pwm>    # Motor velocity (-255 to 255)
BLADE <value>                  # Cutting blade PWM (-255 to 255)
ARM                            # Arm motors (enable drive)
STOP                           # Stop motors immediately
BRAKE ALL <1|0>                # Engage/disengage brakes
DIRINV L <1|0>                 # Invert left motor direction
DIRINV R <1|0>                 # Invert right motor direction
STAT                           # Request status
```

**Parameters:**
```python
max_pwm: 255 (or 100 for launch_robot.py)
max_lin: 1.0 m/s
max_ang: 2.0 rad/s
wheel_radius: 0.4364 m
wheel_separation: 0.52 m
```

---

#### Blade/Cutting Motor Control
**Source:** `hoverboard_bridge_node.py` line 217-219
```python
def on_blade_pwm(self, msg: Int16):
    val = clamp(int(msg.data), -255, 255)
    self.send_line(f'BLADE {val}')
```

**Topic:** `/blade_pwm` (std_msgs/Int16)
- Accepts PWM values: -255 to +255
- Maps directly to Arduino BLADE command

---

### PWM Control Flow Diagram
```
1. Web UI / ROS Topic → /cmd_vel (Twist)
2. cmd_vel_gate.py → /cmd_vel_motors (checks charger status)
3. VESC Driver OR Hoverboard Bridge
4. Motor Controllers (CAN or Serial)
5. Physical Motors (L/R propulsion + cutting blade)
```

---

## 4. BLADE/CUTTING SYSTEM

### Cutting Blade Control
- **Topic:** `/blade_pwm` (std_msgs/Int16)
- **Range:** -255 to +255 (negative = reverse, positive = forward)
- **Driver:** Hoverboard Arduino BLADE subsystem
- **No dedicated RPM feedback** (unlike wheel motors)

### Mowing Logic
- **Coverage Path Planning:** Boustrophedon algorithm in `openmower_mission.py`
- **Zone-based Mowing:** Zones are polygons defined by GPS waypoints
- **Route Transitions:** Pre-recorded routes between zones (YAML format)
- **Mow During Transit:** Routes can have `mow_during_transit: false` flag

---

## 5. WEB SERVER (web_server.py)

### Framework & Binding
- **Framework:** Flask + Flask-CORS
- **Port:** 8080 (default, mapped in docker-compose)
- **Template Folder:** `/mnt/nova_ssd/rosmowercompleate/src/rosmower/web`
- **Static Folder:** Same as template folder

### All Flask Routes (43 endpoints)

#### UI Pages (6)
```python
@app.route('/')                          # mode_control.html
@app.route('/camera')                    # camera_control.html
@app.route('/status')                    # status.html
@app.route('/open-mower')
@app.route('/zones')                     # open_mower_control.html
@app.route('/zones/recorder')            # open_mower_control.html (legacy)
@app.route('/mission-setup')             # open_mower_control.html
@app.route('/routes')                    # zone_routes.html
```

#### System API (15 endpoints)
```python
@app.route('/api/ip')                                    # Device IP address
@app.route('/api/status')                               # Container/rosbridge status
@app.route('/api/docker/start')                         # Start rosmower_robot container
@app.route('/api/docker/stop')                          # Stop rosmower_robot container
@app.route('/api/docker/restart')                       # Restart rosmower_robot container
@app.route('/api/command/<cmd>')                        # Execute docker-helper commands
@app.route('/api/container/stop/<container_name>')      # Stop specific container
@app.route('/api/ros/nodes')                            # List active ROS2 nodes/topics
@app.route('/api/process/<name>/status')                # Background process status
@app.route('/api/open-mower/status')                    # Open Mower companion status
@app.route('/api/open-mower/<action>', methods=['POST']) # Start/stop/restart companion
```

#### Zone Management (9 endpoints)
```python
@app.route('/api/zones', methods=['GET'])               # List all zones
@app.route('/api/zones/save', methods=['POST'])         # Save new zone
@app.route('/api/zones/delete/<zone_id>', methods=['DELETE'])
@app.route('/api/zones/<zone_id>', methods=['PATCH'])   # Update zone metadata
@app.route('/api/zones/graph', methods=['GET'])         # Get zone connectivity graph
@app.route('/api/zones/update_priority', methods=['POST'])
@app.route('/api/zone/record/start', methods=['POST'])  # Start recording zone
@app.route('/api/zone/record/stop', methods=['POST'])   # Stop & save zone
@app.route('/api/zone/record/status', methods=['GET'])  # Recording status
@app.route('/api/zone/record/pause', methods=['POST'])
@app.route('/api/zone/record/resume', methods=['POST'])
@app.route('/api/zone/record/cancel', methods=['POST'])
```

#### Route Management (9 endpoints)
```python
@app.route('/api/routes/list', methods=['GET'])         # List all routes
@app.route('/api/routes/record/start', methods=['POST']) # Start route recording
@app.route('/api/routes/record/stop', methods=['POST'])  # Stop & save route
@app.route('/api/routes/record/pause', methods=['POST'])
@app.route('/api/routes/record/resume', methods=['POST'])
@app.route('/api/routes/record/cancel', methods=['POST'])
@app.route('/api/routes/delete/<route_id>', methods=['DELETE'])
@app.route('/api/routes/status', methods=['GET'])        # Recording status
```

#### Dock Management (3 endpoints)
```python
@app.route('/api/dock', methods=['GET'])                # Get dock location
@app.route('/api/dock/save', methods=['POST'])          # Save dock GPS coords
@app.route('/api/dock/command', methods=['POST'])       # Send dock commands
```

#### Battery & Mission (4 endpoints)
```python
@app.route('/api/battery/status', methods=['GET'])      # Battery info
@app.route('/api/mission/params', methods=['GET'])      # Mission parameters
@app.route('/api/mission/params', methods=['POST'])     # Update mission params
```

---

## 6. WEB UI ASSETS

### HTML Files (6,049 lines total)
1. **mode_control.html** (1,206 lines)
   - Main control dashboard
   - Real-time status monitoring
   - Motor arm/disarm controls
   - Mode switching (FULL/DOCK/IDLE)

2. **open_mower_control.html** (608 lines)
   - Zone and route management UI
   - Zone recording interface
   - Route planning visualization
   - Dock location management

3. **zone_recorder.html** (839 lines)
   - Real-time GPS waypoint display
   - Zone boundary recording controls
   - Live area/distance calculation
   - GPS quality indicators

4. **zone_routes.html** (732 lines)
   - Route list and management
   - Route playback visualization
   - Transit time estimation

5. **mission_setup.html** (721 lines)
   - Mission parameters configuration
   - Coverage target settings
   - Zone priority management

6. **camera_control.html** (777 lines)
   - Camera feed streaming
   - Video resolution/FPS controls
   - Camera selection (stereo)

7. **status.html** (414 lines)
   - System health dashboard
   - Sensor readings (IMU, GPS, LiDAR)
   - Network diagnostics

### JavaScript Integration
- **ROS.js Library:** v1.0 CDN (roslib.min.js)
- **WebSocket Bridge:** ROSBridge at port 9090 for topic publishing/subscribing
- **Real-time Updates:** Subscribers to `/cmd_vel`, `/battery`, `/zones`, etc.

---

## 7. ROUTES DIRECTORY

### Location
`/mnt/nova_ssd/rosmowercompleate/routes/`

### Files
- **README.md** - Route format documentation and best practices
- **.zone_graph_example.yaml** - Example zone connectivity graph

### Route Format (YAML)
```yaml
route_id: "route_001_backyard_to_frontyard"
route_name: "Driveway Route"
from_zone_id: "backyard"
to_zone_id: "frontyard"
route_type: "DRIVEWAY|GATE_PASSAGE|AROUND_BUILDING|NARROW_PATH|ROAD_CROSSING"
bidirectional: true
max_speed_mps: 0.5
path_width_meters: 2.0
mow_during_transit: false
tags: ["paved", "main"]
created_at: "2024-01-15T10:30:00Z"
waypoints:
  - latitude: 37.12345
    longitude: -122.12345
    altitude: 10.5
total_distance_meters: 15.3
estimated_transit_time_seconds: 30.6
```

---

## 8. LAUNCH FILES (29 total)

### Main Launch File
**Path:** `/src/rosmower/launch/launch_robot.launch.py` (416 lines)

**Key Launch Arguments:**
```python
use_sim_time: false
use_ros2_control: false
use_twist_mux: false
use_mavros: true (default)
use_stereo_camera: true
use_vesc: true
use_rosbridge: true
use_mqtt_bridge: false (default)
arm: true (enable motor arming)
dev: /dev/serial/by-id/usb-ArduPilot_SpeedyBeeF405WING_310037000850314E41313720-if00
```

**Included Sub-Launches:**
- `rsp.launch.py` - Robot state publisher
- `icm20948.launch.py` - IMU driver
- `vesc_driver.launch.py` - Motor controllers
- `mqtt_bridge.launch.py` (optional)

**Nodes Started:**
1. Battery Splitter (reads `/mavros/battery` → `/voltage`, `/percent`, `/current`)
2. Battery Monitor (detects charging, triggers dock return)
3. Stereo Camera Viewer (IMX219 CSI cameras)
4. Joint State Publisher
5. ICM20948 IMU Driver
6. IMU Bridge (MAVROS IMU → standard format)
7. EKF Filter (robot_localization)
8. Mode Manager (runtime mode switching)
9. RPLidar Motor Control
10. RPLidar C1 Driver
11. TOF to Scan (time-of-flight sensor)
12. cmd_vel Gate (blocks motor commands when charger connected)
13. MAVROS Node
14. VESC Driver (if use_vesc=true)
15. ROSBridge WebSocket (port 9090)
16. Hoverboard Bridge (if arm=true AND not ros2_control)

### Secondary Launch Files
- **mavros_usb_min.launch.py** - Minimal MAVROS-only setup
- **hoverboard_bridge_only.launch.py** - Motor control only
- **openmower_bringup.launch.py** - Integration with open_mower_next stack
- **vesc_driver.launch.py** - Standalone VESC motor controller

### Launch File Parameters
| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| `dev` | string | `/dev/serial/by-id/usb-ArduPilot_SpeedyBeeF405WING_310037000850314E41313720-if00` | MAVROS FCU serial device |
| `arm` | bool | true | Enable motor arming on startup |
| `use_vesc` | bool | true | Enable VESC differential drive motors |
| `use_stereo_camera` | bool | true | Enable stereo camera pipeline |
| `use_mavros` | bool | true | Enable MAVROS flight controller bridge |
| `use_rosbridge` | bool | true | Enable WebSocket bridge for web UI |

---

## 9. DOCKER COMPOSE

### docker-compose.yml (Standard)
```yaml
services:
  rosmower:           # Main robot container
    build: Dockerfile (target: runtime)
    image: rosmower:latest
    privileged: true
    network_mode: host
    volumes:
      - /dev:/dev                     # USB device access
      - /run/udev:/run/udev:ro        # Device persistence
      - ./logs:/ws/logs               # Log persistence
      - ./cyclonedds.xml:/ws/cyclonedds.xml:ro
      - /tmp/.X11-unix:/tmp/.X11-unix:rw  # X11 forwarding
      - /tmp/argus_socket:/tmp/argus_socket  # Jetson camera socket
    devices:
      - /dev/ttyACM0:/dev/ttyACM0     # MAVROS FCU
      - /dev/ttyUSB0:/dev/ttyUSB0     # Backup serial
      - /dev/ttyTHS1:/dev/ttyTHS1     # RTK GPS rover
      - /dev/i2c-7:/dev/i2c-1         # IMU I2C
      - /dev/video0-3:/dev/video0-3   # Cameras
      - /dev/media0-1:/dev/media0-1   # Media devices
    command: >
      source /opt/ros/humble/setup.bash &&
      source /ws/install/setup.bash &&
      ros2 launch rosmower launch_robot.launch.py

  rviz:              # Optional visualization
    (same image as rosmower)
    command: rviz2 /root/test.rviz
    profiles: [gui]

  dev:               # Development shell
    (same image as rosmower)
    privileged: true
    volumes_from: rosmower + additional mounts
    command: bash
    profiles: [dev]
```

### docker-compose-multi.yml (Multi-Zone Variant)
- Uses Zenoh networking for multi-robot coordination
- Adds zone-specific containers
- Includes RTK GPS base station coordination

**Device Mappings:**
```yaml
/dev/ttyACM0  → MAVROS FCU (ArduPilot)
/dev/ttyUSB0  → Backup serial
/dev/ttyUSB1  → Additional serial
/dev/ttyTHS1  → RTK GPS rover (Jetson)
/dev/ttyAMA0  → GPIO UART for GPS
/dev/i2c-7    → IMU I2C (mapped as i2c-1)
/dev/video0-3 → Camera devices
```

---

## 10. CUSTOM INTERFACES (rosmower_msgs)

### Messages (11 .msg files)

| Message | Purpose |
|---------|---------|
| **BatteryStatus.msg** | Enhanced battery monitoring (voltage, current, temp, state) |
| **Mission.msg** | Mission definition (type, zone_ids, priority, status, timing) |
| **Route.msg** | Route definition (waypoints, bidirectional, distance, eta) |
| **RouteArray.msg** | Array of routes |
| **Zone.msg** | Zone polygon (id, name, priority, coverage, enabled) |
| **ZoneArray.msg** | Array of zones |
| **ZoneGraph.msg** | Zone connectivity graph (nodes + edges) |
| **ZoneGraphNode.msg** | Zone node with priority, mow time, last_mowed |
| **ZoneGraphEdge.msg** | Connection between zones with distance/time |
| **ZoneRecordingStatus.msg** | Real-time zone recording state (waypoints, area, GPS quality) |
| **RouteRecordingStatus.msg** | Real-time route recording state |

### Services (16 .srv files)

| Service | Purpose |
|---------|---------|
| **StartZoneRecording.srv** | Begin zone boundary recording |
| **StopZoneRecording.srv** | End and save zone with options |
| **ControlZoneRecording.srv** | Pause/resume/cancel active recording |
| **SaveZone.srv** | Persist zone to disk |
| **LoadZone.srv** | Load zone from disk |
| **ListZones.srv** | List all saved zones |
| **DeleteZone.srv** | Delete zone from disk |
| **UpdateZoneMetadata.srv** | Update priority, mow time, etc. |
| **StartRouteRecording.srv** | Begin route recording |
| **StopRouteRecording.srv** | End and save route |
| **ControlRouteRecording.srv** | Pause/resume/cancel |
| **DeleteRoute.srv** | Delete route |
| **PlanRoute.srv** | Find route between two zones |
| **GenerateCoveragePath.srv** | Generate boustrophedon coverage for zone |
| **GetZoneGraph.srv** | Retrieve zone connectivity graph |
| **ListRoutes.srv** | List available routes |

---

## 11. EXISTING NODE ARCHITECTURE

### Key Python Nodes

#### 1. **hoverboard_bridge_node.py**
- **Topic Subscriptions:**
  - `/cmd_vel` (geometry_msgs/Twist) → Motor velocity commands
  - `/blade_pwm` (std_msgs/Int16) → Cutting blade PWM
  - `/enable_motors` (std_msgs/Bool) → Motor enable/disable
- **Topic Publications:**
  - `driver_state` (std_msgs/String) → Serial status messages
  - `joint_states` (sensor_msgs/JointState) → Wheel odometry
  - `odom` (nav_msgs/Odometry) → Wheel-based odometry (if enabled)
- **Services Offered:**
  - `arm` (std_srvs/Trigger) → Arm motors
  - `stop` (std_srvs/Trigger) → Stop motors
  - `brake` (std_srvs/SetBool) → Engage/disengage brakes
  - `dirinv_left`, `dirinv_right` (std_srvs/SetBool) → Invert motor direction

#### 2. **battery_monitor.py**
- **Subscriptions:**
  - `/percent` (std_msgs/Float32) → Battery percentage
  - `/current` (std_msgs/Float32) → Battery current
- **Publications:**
  - `/battery/state` (std_msgs/String) → State (NORMAL, LOW, CRITICAL, CHARGING, CHARGED)
  - `/battery/low` (std_msgs/Bool) → Low battery flag
  - `/mission/command` (std_msgs/String) → Mission commands (RETURN_TO_DOCK, EMERGENCY_DOCK)
  - `/robot_mode_cmd` (std_msgs/String) → Mode commands (charging, idle)
- **Parameters:**
  - low_battery_threshold: 25%
  - critical_battery_threshold: 15%
  - charged_threshold: 95%
  - charging_current_threshold: -1.0 A

#### 3. **zone_recorder.py** (GPS Zone Recording)
- **Subscriptions:**
  - `/gps/fix` (sensor_msgs/NavSatFix) → GPS waypoints
  - `/visual_odometry/pose` (geometry_msgs/PoseStamped) → Optional visual odometry
- **Services Offered:**
  - `StartZoneRecording` → Begin recording
  - `StopZoneRecording` → End and save
  - `ControlZoneRecording` → Pause/resume/cancel
- **Features:**
  - Intelligent waypoint sampling (minimum distance threshold)
  - Douglas-Peucker polygon simplification
  - Real-time area calculation (Shoelace formula)
  - GPS quality monitoring (RTK float/fixed detection)

#### 4. **zone_manager.py**
- **Publications:**
  - `/zones` (rosmower_msgs/ZoneArray) → All zones
  - `/zone/current` (rosmower_msgs/Zone) → Currently active zone
  - `/zones/graph` (rosmower_msgs/ZoneGraph) → Zone connectivity
- **Services Offered:**
  - `/zone/save`, `/zone/load`, `/zone/list`, `/zone/delete`
  - `/zone/graph` → Get connectivity graph
  - `/route/plan` → Find routes between zones
- **Storage:** YAML files in `/ws/zones/` directory

#### 5. **cmd_vel_gate.py** (Motor Lockout)
- **Subscriptions:**
  - `/current` (std_msgs/Float32) → Battery current
- **Publications:**
  - `/cmd_vel_motors` (geometry_msgs/Twist) → Gated velocity commands
- **Function:** Blocks motor commands when charger is connected (current < -1.0 A)

#### 6. **battery_splitter.py**
- **Subscriptions:**
  - `/mavros/battery` (sensor_msgs/BatteryState)
- **Publications:**
  - `/voltage` (std_msgs/Float32)
  - `/percent` (std_msgs/Float32)
  - `/current` (std_msgs/Float32)
- **Function:** Splits battery message into individual topics for legacy compatibility

#### 7. **imu_bridge.py**
- **Subscriptions:** `/mavros/imu/data` (sensor_msgs/Imu)
- **Publications:** `/imu/data_raw` (sensor_msgs/Imu)
- **Function:** Relays IMU from MAVROS to standard ROS2 naming

#### 8. **mode_manager.py**
- **Subscriptions:**
  - `/robot_mode_cmd` (std_msgs/String) → Mode commands
- **Publications:**
  - `/robot_mode` (std_msgs/String) → Current mode
- **Modes:** FULL, DOCK, IDLE, CHARGING

#### 9. **rplidar_motor_control.py**
- **Function:** Auto-starts/stops RPLidar motor when nodes are detected
- **Watches for:** rviz, move_base node lifecycle

### C++ Nodes

#### **vesc_driver_node** (vesc_driver package)
- **Subscriptions:**
  - `/cmd_vel_motors` (geometry_msgs/Twist) → Motor commands
- **Publications:**
  - `/wheel_joint_states` (sensor_msgs/JointState) → Wheel encoder feedback
  - `/odom` (nav_msgs/Odometry) → Wheel odometry
- **CAN Interface:** VESC ID 0 (USB), ID 5 (CAN bus)
- **Control Mode:** Duty cycle PWM (0-100%)

---

## 12. MAVLink/MAVProxy Configuration

### mav.parm (Parameter File)
**Location:** `/mnt/nova_ssd/rosmowercompleate/mav.parm`

**Sample Parameters (first 50 lines):**
```
ACRO_TURN_RATE   180.0
AHRS_COMP_BETA   0.1
AHRS_EKF_TYPE    3
AHRS_GPS_USE     1
ARMING_CHECK     1
ATC_ACCEL_MAX    1.0
ATC_BRAKE        1
...and 100+ more
```

**Purpose:** Parameter upload to ArduPilot-compatible FCU (SpeedyBee F405 WING)

### sources.yaml (Telemetry Configuration)
**Location:** `/mnt/nova_ssd/rosmowercompleate/sources.yaml`

**Defines telemetry topics for monitoring:**
```yaml
- name: Battery
  topic: /mavros/battery
  type: sensor_msgs/msg/BatteryState
  fields:
    - {label: Voltage, path: voltage, fmt: "{:.2f} V"}
    - {label: Pct, path: percentage, fmt: "{:.0%}"}
    - {label: Current, path: current, fmt: "{:.2f} A"}

- name: GPS
  topic: /gps/fix
  type: sensor_msgs/msg/NavSatFix
  fields:
    - {label: Lat, path: latitude, fmt: "{:.6f}"}
    - {label: Lon, path: longitude, fmt: "{:.6f}"}
    - {label: Alt, path: altitude, fmt: "{:.2f} m"}

- name: IMU
  topic: /imu
  type: sensor_msgs/msg/Imu
  ...
```

---

## 13. DOCUMENTATION (80+ files)

### Quick Start Guides
- `00-START-HERE.md` - Initial setup
- `00-ZONE-RECORDING-START-HERE.md` - Zone recording tutorial
- `00-MULTI-ZONE-START-HERE.md` - Multi-robot setup
- `QUICKSTART_WEB_CONTROL.md` - Web UI usage
- `QUICKSTART_MODE_CONTROL.md` - Mode management

### Architecture & Design
- `ARCHITECTURE_ANALYSIS.md` - Detailed system design
- `ARCHITECTURE_SUMMARY.txt` - High-level overview
- `ZONE_RECORDING_ARCHITECTURE.md` - Zone recording system
- `MULTI_ZONE_ARCHITECTURE.txt` - Multi-robot coordination

### Implementation Guides
- `IMPLEMENTATION_CHECKLIST.md` - Setup checklist
- `VESC_INTEGRATION_GUIDE.md` - Motor controller setup
- `ROUTE_RECORDING_GUIDE.md` - Route creation workflow
- `RTK_GPS_SETUP.md` - GPS configuration
- `CAMERA_SETUP.md` - Stereo camera integration

### Troubleshooting
- `gps_troubleshooting.md` - GPS issues
- `LIDAR_DIAGNOSTIC_REPORT.md` - LiDAR diagnostics
- `README-LIDAR-FIX.md` - LiDAR fixes

---

## 14. PACKAGE.XML DEPENDENCIES

### rosmower Package
```xml
<buildtool_depend>ament_cmake</buildtool_depend>
<exec_depend>rclpy</exec_depend>
<exec_depend>rclcpp</exec_depend>
<exec_depend>geometry_msgs</exec_depend>
<exec_depend>sensor_msgs</exec_depend>
<exec_depend>std_msgs</exec_depend>
<exec_depend>rosmower_msgs</exec_depend>
<exec_depend>nav_msgs</exec_depend>
<exec_depend>mqtt_bridge</exec_depend>
```

### vesc_driver Package
```xml
<depend>rclcpp</depend>
<depend>std_msgs</depend>
<depend>geometry_msgs</depend>
<depend>sensor_msgs</depend>
<depend>nav_msgs</depend>
<depend>tf2</depend>
<depend>tf2_geometry_msgs</depend>
```

### openmower_mission Package
```xml
<depend>rclpy</depend>
<depend>std_msgs</depend>
<depend>std_srvs</depend>
<depend>geometry_msgs</depend>
<depend>sensor_msgs</depend>
<depend>nav_msgs</depend>
<depend>action_msgs</depend>
<depend>rosmower_msgs</depend>
```

---

## SUMMARY

This ROS2 Humble repository implements a **fully autonomous lawn mower** with:

✅ **Hardware Control:**
- VESC differential drive motors (duty cycle PWM)
- Cutting blade motor control
- Battery management & charger detection
- RTK GPS for precise zone/route recording
- Stereo cameras (IMX219) with hardware acceleration
- RPLidar C1 for obstacle detection
- ICM20948 IMU for stability control

✅ **Navigation & Mapping:**
- MAVROS integration for flight controller
- EKF-based localization (robot_localization)
- Zone-based coverage path planning (boustrophedon)
- Route recording with GPS waypoints
- Zone graph for connectivity analysis

✅ **Web-Based Control:**
- 43 Flask API endpoints
- Real-time ROS2 bridge (port 9090)
- Zone & route management UI
- Battery monitoring dashboard
- Dock location management

✅ **Customization:**
- 16 ROS2 services for zone/route management
- 11 custom message types
- Launch file parameters for hardware configuration
- Mode manager for runtime switching
- MQTT integration for Home Assistant

✅ **Documentation:**
- 80+ implementation & troubleshooting guides
- Architecture analysis documents
- Quick-start tutorials for each subsystem

