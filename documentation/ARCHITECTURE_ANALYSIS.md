Perfect! Now I have enough information. Let me create the comprehensive architectural analysis and recommendations.

---

# 🤖 COMPREHENSIVE ARCHITECTURAL ANALYSIS
## ROS2 Autonomous Mowing Robot

---

## 📊 EXECUTIVE SUMMARY

### Current State Assessment

**✅ STRENGTHS:**
- **Solid hardware foundation**: Jetson Orin Nano, RTK GPS, RPLiDAR A1, IMX219 stereo cameras, ICM20948 IMU, hoverboard motor controller
- **Docker containerization**: Well-structured deployment with Docker Compose
- **ROS2 Humble integration**: Proper use of modern ROS2 features
- **Sensor fusion**: EKF-based localization combining wheel odometry, IMU, and GPS
- **Mode management system**: Runtime mode switching (idle, charging, mowing, full)
- **Web interface**: Basic control panel for mode switching and system commands
- **Nav2 integration**: Navigation stack configured and ready

**❌ CRITICAL GAPS:**
- **NO zone management system**: Cannot define, store, or manage mowing zones
- **NO autonomous path planning**: No coverage path planner or random path generation
- **NO battery management logic**: No dock return, no charge monitoring, no resume-after-charge
- **NO AprilTag detection**: Charging dock detection not implemented
- **NO obstacle avoidance behavior**: LiDAR present but no autonomous obstacle handling
- **NO mission planner**: No high-level autonomy to orchestrate zone → path → mow → charge cycles
- **Limited web UI**: No zone drawing, no real-time visualization, no mission management

**System Maturity**: 🟡 **Foundation Phase** (30% complete)
- Core infrastructure: ✅ Complete
- Sensor integration: ✅ Complete
- Autonomous behaviors: ❌ Missing
- Zone management: ❌ Missing
- Mission planning: ❌ Missing

---

## 📁 PHASE 1: SYSTEM DISCOVERY

### 1.1 Codebase Structure

```
rosmowercompleate/
├── src/
│   ├── rosmower/                    # Main robot package
│   │   ├── scripts/                 # 13 Python nodes
│   │   │   ├── mode_manager.py      # Mode control (idle/charging/mowing/full)
│   │   │   ├── hoverboard_bridge_node.py  # Motor control + odometry
│   │   │   ├── battery_splitter.py  # Battery data parsing
│   │   │   ├── imu_bridge.py        # IMU data bridging
│   │   │   ├── rplidar_motor_control.py  # LiDAR power management
│   │   │   ├── lidar_scan_guard.py  # LiDAR safety monitoring
│   │   │   ├── relay_control_node.py  # GPIO relay (blade control?)
│   │   │   ├── tof_guard.py         # ToF sensor safety
│   │   │   ├── tof_to_scan.py       # ToF → LaserScan conversion
│   │   │   ├── vl53_bridge.py       # VL53 ToF sensor bridge
│   │   │   ├── camera_lifecycle_wrapper.py  # Camera management
│   │   │   ├── image_flip_node.py   # Image processing
│   │   │   └── stabilitty.py        # Stability monitoring
│   │   ├── launch/                  # 19 launch files
│   │   ├── config/                  # Nav2, EKF, camera, twist_mux configs
│   │   ├── description/             # URDF/xacro robot models
│   │   └── web/                     # HTML control interfaces
│   ├── gps_rtk/                     # RTK GPS integration (LC29HDA)
│   ├── icm20948_imu_driver/         # IMU driver
│   ├── sllidar_ros2/                # RPLiDAR driver
│   ├── diffdrive_arduino/           # Motor control (unused?)
│   ├── mqtt_bridge/                 # MQTT integration
│   ├── stereo_camera_viewer/        # Stereo camera handling
│   └── hailo_ros/                   # AI accelerator (future use?)
├── web_server.py                    # Flask web server for control
├── docker-compose.yml               # Container orchestration
└── cyclonedds.xml                   # DDS configuration
```

### 1.2 Current ROS2 Node Architecture

**Active Nodes (from launch_robot.launch.py):**

```
┌─────────────────────────────────────────────────────────────┐
│                    ROBOT ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────┘

HARDWARE LAYER
├── Hoverboard Bridge (/hoverboard_bridge)
│   ├── Subscribes: /cmd_vel, /blade_pwm, /enable_motors
│   ├── Publishes: /wheel/odom, /joint_states, /driver_state
│   └── Hardware: Arduino serial @ /dev/serial/by-id/usb-1a86_USB_Serial
│
├── RPLiDAR (/rplidar)
│   ├── Publishes: /scan (LaserScan)
│   └── Hardware: /dev/serial/by-id/usb-Silicon_Labs_CP2102...
│
├── GPS/RTK (MAVROS /mavros/global_position/local)
│   ├── Publishes: GPS coordinates, heading
│   └── Hardware: LC29HDA @ /dev/ttyTHS1, RTCM corrections from base
│
├── IMU (/mavros/imu/data → /imu_bridge → /imu/data_raw)
│   └── Hardware: ICM20948 via MAVROS
│
├── Cameras (/v4l2_camera)
│   ├── Stereo IMX219 CSI cameras
│   └── Publishes: /camera/image_raw, camera_info
│
└── Battery Monitor (/mavros/battery → /battery_splitter)
    └── Publishes: /voltage, /percent, /current

LOCALIZATION LAYER
└── EKF Node (/ekf_filter_node)
    ├── Fuses: wheel odometry + IMU + GPS
    ├── Publishes: /odom (nav_msgs/Odometry)
    └── Outputs: Filtered pose in odom frame

CONTROL LAYER
├── Mode Manager (/mode_manager)
│   ├── Subscribes: /robot_mode_cmd
│   ├── Publishes: /robot_mode, /enable_motors, /enable_sensors, etc.
│   └── Modes: idle, charging, mowing, full
│
└── (Nav2 stack - configured but not launched by default)

WEB INTERFACE
└── Flask Server (external, port 8080)
    ├── Mode switching UI
    ├── Camera control
    └── System status monitoring
```

### 1.3 Data Flow Analysis

**Current Topics:**

| Topic | Type | Publisher | Subscriber | Purpose |
|-------|------|-----------|------------|---------|
| `/cmd_vel` | Twist | Nav2 (future) | hoverboard_bridge | Motor commands |
| `/scan` | LaserScan | rplidar | Nav2 (future) | Obstacle detection |
| `/wheel/odom` | Odometry | hoverboard_bridge | ekf_filter_node | Wheel odometry |
| `/imu/data_raw` | Imu | imu_bridge | ekf_filter_node | IMU data |
| `/mavros/global_position/local` | Odometry | mavros | ekf_filter_node | GPS position |
| `/odom` | Odometry | ekf_filter_node | Nav2 (future) | Filtered localization |
| `/voltage`, `/percent`, `/current` | Float32 | battery_splitter | (none) | Battery status |
| `/robot_mode` | String | mode_manager | (none) | Current mode |
| `/enable_motors` | Bool | mode_manager | hoverboard_bridge | Motor enable/disable |

**Missing Critical Topics:**
- ❌ No `/zone/current` - current active zone
- ❌ No `/mission/status` - mission state
- ❌ No `/coverage/progress` - mowing coverage tracking
- ❌ No `/dock/pose` - charging dock location
- ❌ No `/battery/return_threshold` - low battery trigger

### 1.4 Nav2 Configuration Assessment

**✅ Configured Components:**
- AMCL localization (though not needed with GPS)
- DWB local planner (trajectory following)
- NavFn global planner (A* pathfinding)
- Behavior server (spin, backup, wait)
- Costmap configuration (local + global)

**❌ Missing for Autonomous Mowing:**
- Coverage path planner plugin
- Zone-based planning
- Battery-aware planning
- Obstacle memory/persistence
- Dynamic replanning for coverage

---

## 🔍 PHASE 2: GAP ANALYSIS

### Priority Matrix

```
┌─────────────────────────────────────────────────────────┐
│  IMPACT vs EFFORT ANALYSIS                              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  HIGH IMPACT, LOW EFFORT (DO FIRST) 🟢                  │
│  ├── Battery monitoring & threshold alerts              │
│  ├── Zone storage system (JSON/YAML files)              │
│  └── Basic web UI for zone drawing                      │
│                                                          │
│  HIGH IMPACT, MEDIUM EFFORT (DO NEXT) 🟡                │
│  ├── Coverage path planner integration                  │
│  ├── Mission state machine (orchestrator)               │
│  ├── Obstacle avoidance with Nav2                       │
│  └── Zone transition logic                              │
│                                                          │
│  HIGH IMPACT, HIGH EFFORT (CRITICAL BUT COMPLEX) 🔴     │
│  ├── AprilTag dock detection & alignment                │
│  ├── Resume-after-charge with coverage memory           │
│  ├── Adaptive path replanning                           │
│  └── GPS drift compensation & fence handling            │
│                                                          │
│  MEDIUM IMPACT (FUTURE ENHANCEMENTS) ⚪                  │
│  ├── Terrain analysis & adaptive speed                  │
│  ├── Weather awareness                                  │
│  ├── Stereo vision obstacle detection                   │
│  └── Multi-robot coordination                           │
└─────────────────────────────────────────────────────────┘
```

### Detailed Gap Breakdown

#### 🔴 **GAP 1: No Zone Management System**
**Impact**: Cannot define where to mow
**Current State**: No zone definition, storage, or loading capability
**Required**:
- Zone definition format (polygon vertices in GPS/odom coordinates)
- Zone storage (YAML/JSON files)
- Zone loader/manager node
- Zone priority and scheduling
- Zone transition planning

#### 🔴 **GAP 2: No Autonomous Path Planning**
**Impact**: Cannot execute autonomous mowing
**Current State**: Nav2 configured but no coverage planner
**Required**:
- Coverage path planner (boustrophedon, spiral, or random)
- Path generation within zone boundaries
- Path optimization for battery efficiency
- Obstacle-aware replanning

#### 🔴 **GAP 3: No Battery Management**
**Impact**: Cannot autonomously manage power
**Current State**: Battery data published but not monitored
**Required**:
- Battery state monitoring node
- Low-battery detection & dock return trigger
- Charging state detection
- Resume mission after charge logic

#### 🔴 **GAP 4: No Dock Detection System**
**Impact**: Cannot autonomously return to charge
**Current State**: No AprilTag detection or dock navigation
**Required**:
- AprilTag detection node (apriltag_ros)
- Dock pose estimation
- Precision docking controller
- Charge contact verification

#### 🟡 **GAP 5: Limited Obstacle Avoidance**
**Impact**: Cannot safely navigate around obstacles
**Current State**: LiDAR active, Nav2 costmap configured, but no autonomous behaviors
**Required**:
- Obstacle detection & classification
- Dynamic obstacle handling
- Recovery behaviors (back up, repath, skip area)
- Obstacle persistence (don't retry same blocked area)

#### 🟡 **GAP 6: No Mission Orchestration**
**Impact**: Cannot execute complex multi-zone missions
**Current State**: Mode manager exists but no high-level autonomy
**Required**:
- Mission state machine (IDLE → PLAN → MOW → LOW_BATTERY → DOCK → CHARGE → RESUME)
- Zone sequencing logic
- Mission pause/resume
- Error recovery

#### 🟡 **GAP 7: Minimal Web UI**
**Impact**: Difficult to configure and monitor
**Current State**: Mode switching only, no visualization
**Required**:
- Interactive zone drawing (map interface)
- Real-time robot position & zone visualization
- Mission progress tracking
- Battery & sensor status dashboard
- Manual control override

---

## 🏗️ PHASE 3: DETAILED RECOMMENDATIONS

### 🎯 Recommended Architecture: Three-Layer System

```
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 1: MISSION PLANNING                     │
│  ┌────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Mission Manager│  │ Zone Manager    │  │ Battery Manager │  │
│  │ (orchestrator) │◄─┤ (zone DB + load)│  │ (monitor + dock)│  │
│  └────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
           │ publishes goals                   │ battery alerts
           ▼                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 2: NAVIGATION & PLANNING                │
│  ┌────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Coverage Path  │  │ Nav2 Stack      │  │ Dock Navigator  │  │
│  │ Planner        │─►│ (global + local)│  │ (AprilTag align)│  │
│  └────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
           │ cmd_vel                           │ dock approach
           ▼                                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                    LAYER 3: HARDWARE CONTROL                     │
│  ┌────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │ Motor Control  │  │ Sensor Fusion   │  │ Safety Monitor  │  │
│  │ (hoverboard)   │  │ (EKF)           │  │ (obstacle halt) │  │
│  └────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚀 IMPLEMENTATION ROADMAP

### **PHASE A: Foundation (Week 1-2) - HIGH Priority 🔴**

#### A1. Battery Management System

**New Node**: `battery_monitor.py`

```python
#!/usr/bin/env python3
"""
Battery Monitor & Management Node
Monitors battery state and triggers dock return when low
"""

class BatteryMonitor(Node):
    def __init__(self):
        # Parameters
        self.declare_parameter('low_battery_threshold', 20.0)  # percent
        self.declare_parameter('critical_battery_threshold', 15.0)
        self.declare_parameter('charged_threshold', 95.0)
        self.declare_parameter('charging_current_threshold', 0.1)  # A
        
        # Subscribers
        self.create_subscription(Float32, '/percent', self.battery_callback, 10)
        self.create_subscription(Float32, '/current', self.current_callback, 10)
        
        # Publishers
        self.battery_state_pub = self.create_publisher(String, '/battery/state', 10)
        self.low_battery_pub = self.create_publisher(Bool, '/battery/low', 10)
        self.mission_control_pub = self.create_publisher(String, '/mission/command', 10)
        
        # State tracking
        self.battery_percent = 100.0
        self.current_state = 'NORMAL'  # NORMAL, LOW, CRITICAL, CHARGING, CHARGED
        
    def battery_callback(self, msg):
        self.battery_percent = msg.data
        self.update_state()
        
    def update_state(self):
        # State machine for battery management
        if self.battery_percent < self.critical_threshold:
            self.transition_to('CRITICAL')
            self.mission_control_pub.publish(String(data='EMERGENCY_DOCK'))
        elif self.battery_percent < self.low_threshold:
            self.transition_to('LOW')
            self.mission_control_pub.publish(String(data='RETURN_TO_DOCK'))
        # ... charging detection logic
```

**Topics Created:**
- `/battery/state` (String): NORMAL | LOW | CRITICAL | CHARGING | CHARGED
- `/battery/low` (Bool): Low battery alert
- `/mission/command` (String): Commands to mission manager

**Integration**: Subscribes to existing `/percent` and `/current` from battery_splitter

**Config**: `config/battery_manager.yaml`
```yaml
battery_monitor:
  ros__parameters:
    low_battery_threshold: 25.0      # Start return to dock
    critical_battery_threshold: 15.0  # Emergency dock now
    charged_threshold: 95.0           # Resume mission
    charging_current_threshold: 0.1   # Detect charging state
    check_rate: 1.0                   # Hz
```

---

#### A2. Zone Management System

**New Node**: `zone_manager.py`

```python
#!/usr/bin/env python3
"""
Zone Manager - Loads, stores, and manages mowing zones
"""

from geometry_msgs.msg import PolygonStamped, Point32
from rosmower_msgs.msg import Zone, ZoneArray  # Custom messages
from rosmower_msgs.srv import SaveZone, LoadZone, ListZones

class ZoneManager(Node):
    def __init__(self):
        self.declare_parameter('zone_directory', '/ws/zones')
        self.declare_parameter('default_frame', 'map')
        
        # Storage
        self.zones = {}  # zone_id -> Zone message
        
        # Services
        self.create_service(SaveZone, '/zone/save', self.save_zone_callback)
        self.create_service(LoadZone, '/zone/load', self.load_zone_callback)
        self.create_service(ListZones, '/zone/list', self.list_zones_callback)
        
        # Publishers
        self.zone_array_pub = self.create_publisher(ZoneArray, '/zones', 10)
        self.current_zone_pub = self.create_publisher(Zone, '/zone/current', 10)
        
        # Load zones from disk on startup
        self.load_all_zones()
        
    def save_zone_callback(self, request, response):
        """Save zone to YAML file"""
        zone = request.zone
        filename = f"{self.zone_dir}/{zone.id}.yaml"
        
        zone_dict = {
            'id': zone.id,
            'name': zone.name,
            'priority': zone.priority,
            'frame_id': zone.polygon.header.frame_id,
            'vertices': [
                {'x': p.x, 'y': p.y} 
                for p in zone.polygon.polygon.points
            ]
        }
        
        with open(filename, 'w') as f:
            yaml.dump(zone_dict, f)
        
        self.zones[zone.id] = zone
        response.success = True
        return response
```

**Custom Messages** (create `rosmower_msgs` package):

`msg/Zone.msg`:
```
string id
string name
uint8 priority          # 1-10, higher = mow first
geometry_msgs/PolygonStamped polygon
bool enabled
float64 coverage_percent  # Track completion
```

`msg/ZoneArray.msg`:
```
Header header
Zone[] zones
```

`srv/SaveZone.srv`:
```
Zone zone
---
bool success
string message
```

**Zone File Format** (`zones/front_yard.yaml`):
```yaml
id: "front_yard"
name: "Front Yard"
priority: 5
frame_id: "map"
vertices:
  - {x: 10.5, y: 20.3}
  - {x: 15.2, y: 20.1}
  - {x: 15.0, y: 25.8}
  - {x: 10.3, y: 25.9}
enabled: true
coverage_percent: 0.0
```

**Directory Structure**:
```
/ws/zones/
├── front_yard.yaml
├── back_yard.yaml
├── side_strip.yaml
└── zones_index.yaml  # Metadata
```

---

#### A3. Web UI - Zone Drawing Interface

**Enhanced Web Server** (`web_server.py` additions):

```python
@app.route('/zone_manager')
def zone_manager():
    """Serve zone management interface"""
    return send_from_directory('/mnt/nova_ssd/rosmowercompleate/src/rosmower/web', 'zone_manager.html')

@app.route('/api/zones')
def get_zones():
    """Get all zones via ROS2 service"""
    # Call /zone/list service
    result = call_ros2_service('rosmower_msgs/srv/ListZones', '/zone/list', {})
    return jsonify(result)

@app.route('/api/zones/save', methods=['POST'])
def save_zone():
    """Save zone via ROS2 service"""
    zone_data = request.json
    # Call /zone/save service
    result = call_ros2_service('rosmower_msgs/srv/SaveZone', '/zone/save', zone_data)
    return jsonify(result)
```

**New Web Page** (`web/zone_manager.html`):
```html
<!DOCTYPE html>
<html>
<head>
    <title>Zone Manager</title>
    <script src="https://cdn.jsdelivr.net/npm/roslib@1/build/roslib.min.js"></script>
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
    <script src="https://unpkg.com/leaflet-draw@1.0.4/dist/leaflet.draw.js"></script>
</head>
<body>
    <div id="map" style="height: 600px;"></div>
    
    <div class="controls">
        <h3>Zones</h3>
        <ul id="zone-list"></ul>
        <button onclick="drawNewZone()">Draw New Zone</button>
        <button onclick="saveZones()">Save Zones</button>
    </div>
    
    <script>
        // Initialize Leaflet map with robot's GPS position as center
        const map = L.map('map').setView([39.7392, -104.9903], 18);
        
        // Use satellite imagery
        L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            attribution: 'Esri'
        }).addTo(map);
        
        // Enable drawing controls
        const drawnItems = new L.FeatureGroup();
        map.addLayer(drawnItems);
        
        const drawControl = new L.Control.Draw({
            draw: {
                polygon: true,
                polyline: false,
                rectangle: true,
                circle: false,
                marker: false
            },
            edit: {
                featureGroup: drawnItems
            }
        });
        map.addControl(drawControl);
        
        // Handle new polygon drawn
        map.on('draw:created', function(e) {
            const layer = e.layer;
            drawnItems.addLayer(layer);
            
            const zoneName = prompt("Enter zone name:");
            if (zoneName) {
                // Convert Leaflet coordinates to zone format
                const vertices = layer.getLatLngs()[0].map(ll => ({
                    lat: ll.lat,
                    lon: ll.lng
                }));
                
                saveZoneToROS(zoneName, vertices);
            }
        });
        
        function saveZoneToROS(name, vertices) {
            fetch('/api/zones/save', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    name: name,
                    vertices: vertices
                })
            }).then(response => response.json())
              .then(data => {
                  if (data.success) {
                      alert('Zone saved!');
                      loadZones();
                  }
              });
        }
        
        function loadZones() {
            fetch('/api/zones')
                .then(response => response.json())
                .then(zones => {
                    // Display zones on map
                    zones.forEach(zone => {
                        const polygon = L.polygon(
                            zone.vertices.map(v => [v.lat, v.lon])
                        ).addTo(drawnItems);
                        polygon.bindPopup(zone.name);
                    });
                    
                    // Update zone list
                    const list = document.getElementById('zone-list');
                    list.innerHTML = zones.map(z => 
                        `<li>${z.name} (Priority: ${z.priority})</li>`
                    ).join('');
                });
        }
        
        // Load zones on page load
        loadZones();
    </script>
</body>
</html>
```

**GPS Coordinate Conversion**: Add utility to convert GPS (lat/lon) ↔ Map (x/y in meters)

```python
# In zone_manager.py
from pyproj import Proj, transform

class ZoneManager:
    def __init__(self):
        # Use UTM projection for local metric coordinates
        self.gps_datum = 'EPSG:4326'  # WGS84
        self.local_proj = 'EPSG:32613'  # UTM Zone 13N (Colorado example)
        
    def gps_to_map(self, lat, lon):
        """Convert GPS to local map coordinates"""
        easting, northing = transform(
            Proj(self.gps_datum),
            Proj(self.local_proj),
            lon, lat
        )
        return (easting, northing)
        
    def map_to_gps(self, x, y):
        """Convert map coordinates to GPS"""
        lon, lat = transform(
            Proj(self.local_proj),
            Proj(self.gps_datum),
            x, y
        )
        return (lat, lon)
```

---

### **PHASE B: Path Planning & Navigation (Week 3-4) - HIGH Priority 🔴**

#### B1. Coverage Path Planner

**Approach**: Use `coverage_path_planner` ROS2 package or implement boustrophedon algorithm

**Option 1: Use Existing Package**
```bash
# Add to Dockerfile
ros-humble-navigation2 \
ros-humble-nav2-bringup \
ros-humble-nav2-waypoint-follower
```

**Option 2: Custom Random Path Generator** (simpler for MVP)

**New Node**: `random_path_generator.py`

```python
#!/usr/bin/env python3
"""
Random Path Generator for Zone Coverage
Generates random waypoints within zone boundaries
"""

import random
from shapely.geometry import Polygon, Point
from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped

class RandomPathGenerator(Node):
    def __init__(self):
        self.declare_parameter('waypoint_spacing', 2.0)  # meters
        self.declare_parameter('num_waypoints', 50)
        
        # Subscribers
        self.create_subscription(Zone, '/zone/current', self.zone_callback, 10)
        
        # Publishers
        self.path_pub = self.create_publisher(Path, '/path/coverage', 10)
        
        # Services
        self.create_service(Trigger, '/path/generate', self.generate_path_callback)
        
        self.current_zone = None
        
    def zone_callback(self, msg):
        """Store current zone"""
        self.current_zone = msg
        
    def generate_path_callback(self, request, response):
        """Generate random path within current zone"""
        if not self.current_zone:
            response.success = False
            response.message = "No active zone"
            return response
            
        # Create Shapely polygon from zone vertices
        vertices = [(p.x, p.y) for p in self.current_zone.polygon.polygon.points]
        zone_polygon = Polygon(vertices)
        
        # Get bounding box
        minx, miny, maxx, maxy = zone_polygon.bounds
        
        # Generate random points inside polygon
        waypoints = []
        attempts = 0
        max_attempts = self.num_waypoints * 10
        
        while len(waypoints) < self.num_waypoints and attempts < max_attempts:
            # Random point in bounding box
            x = random.uniform(minx, maxx)
            y = random.uniform(miny, maxy)
            point = Point(x, y)
            
            # Check if inside polygon
            if zone_polygon.contains(point):
                waypoints.append((x, y))
            attempts += 1
        
        # Create Path message
        path = Path()
        path.header.frame_id = self.current_zone.polygon.header.frame_id
        path.header.stamp = self.get_clock().now().to_msg()
        
        for x, y in waypoints:
            pose = PoseStamped()
            pose.header = path.header
            pose.pose.position.x = x
            pose.pose.position.y = y
            pose.pose.orientation.w = 1.0  # No specific orientation
            path.poses.append(pose)
        
        self.path_pub.publish(path)
        
        response.success = True
        response.message = f"Generated {len(waypoints)} waypoints"
        return response
```

**Better Option: Boustrophedon (Lawn Mower Pattern)**

```python
def generate_boustrophedon_path(self, zone_polygon, spacing=2.0):
    """Generate back-and-forth lawn mower pattern"""
    minx, miny, maxx, maxy = zone_polygon.bounds
    
    waypoints = []
    y = miny
    direction = 1  # 1 for left-to-right, -1 for right-to-left
    
    while y <= maxy:
        # Create horizontal line at current y
        if direction == 1:
            start_x, end_x = minx, maxx
        else:
            start_x, end_x = maxx, minx
        
        # Sample points along line
        num_points = int((maxx - minx) / spacing)
        for i in range(num_points):
            x = start_x + i * spacing * direction
            point = Point(x, y)
            
            if zone_polygon.contains(point):
                waypoints.append((x, y))
        
        y += spacing
        direction *= -1  # Alternate direction
    
    return waypoints
```

**Integration with Nav2**:
- Publish path to `/path/coverage`
- Use `nav2_waypoint_follower` to execute path
- Configure `nav2_params.yaml` to use waypoint follower

---

#### B2. Mission State Machine

**New Node**: `mission_manager.py`

```python
#!/usr/bin/env python3
"""
Mission Manager - High-level orchestration of mowing missions
State machine: IDLE → PLANNING → MOWING → PAUSED → RETURNING → CHARGING → COMPLETE
"""

from enum import Enum
from rosmower_msgs.msg import MissionState, MissionCommand

class MissionState(Enum):
    IDLE = 0
    PLANNING = 1
    MOWING = 2
    PAUSED = 3
    RETURNING_TO_DOCK = 4
    DOCKING = 5
    CHARGING = 6
    RESUMING = 7
    COMPLETE = 8
    ERROR = 9

class MissionManager(Node):
    def __init__(self):
        super().__init__('mission_manager')
        
        # Parameters
        self.declare_parameter('auto_start', False)
        self.declare_parameter('pause_on_obstacle', True)
        self.declare_parameter('max_mission_duration', 7200.0)  # 2 hours
        
        # State
        self.state = MissionState.IDLE
        self.current_zone = None
        self.coverage_progress = 0.0
        self.mission_start_time = None
        
        # Subscribers
        self.create_subscription(String, '/mission/command', self.command_callback, 10)
        self.create_subscription(String, '/battery/state', self.battery_callback, 10)
        self.create_subscription(Bool, '/obstacle/detected', self.obstacle_callback, 10)
        
        # Publishers
        self.state_pub = self.create_publisher(String, '/mission/state', 10)
        self.zone_cmd_pub = self.create_publisher(String, '/zone/command', 10)
        self.nav_goal_pub = self.create_publisher(PoseStamped, '/goal_pose', 10)
        
        # Service clients
        self.generate_path_client = self.create_client(Trigger, '/path/generate')
        self.load_zone_client = self.create_client(LoadZone, '/zone/load')
        
        # Timer for state machine
        self.create_timer(0.5, self.state_machine_update)
        
        self.get_logger().info('Mission Manager initialized')
    
    def state_machine_update(self):
        """Main state machine logic"""
        
        if self.state == MissionState.IDLE:
            # Waiting for start command
            pass
            
        elif self.state == MissionState.PLANNING:
            # Load next zone and generate path
            self.get_logger().info('Planning mission...')
            
            # Request zone from zone manager
            # Request path from path planner
            # Transition to MOWING when ready
            self.transition_to(MissionState.MOWING)
            
        elif self.state == MissionState.MOWING:
            # Active mowing - monitor progress
            if self.coverage_progress >= 100.0:
                self.get_logger().info('Zone complete!')
                self.transition_to(MissionState.COMPLETE)
            # State transitions handled by callbacks (battery, obstacle)
            
        elif self.state == MissionState.RETURNING_TO_DOCK:
            # Navigate to dock location
            self.get_logger().info('Returning to dock...')
            dock_pose = self.get_dock_pose()  # From parameter or detected
            self.nav_goal_pub.publish(dock_pose)
            # Wait for Nav2 goal completion
            self.transition_to(MissionState.DOCKING)
            
        elif self.state == MissionState.DOCKING:
            # Precision docking with AprilTag
            # (Handled by dock_navigator node)
            pass
            
        elif self.state == MissionState.CHARGING:
            # Monitor battery until charged
            if self.battery_percent >= self.charged_threshold:
                self.get_logger().info('Battery charged, resuming mission')
                self.transition_to(MissionState.RESUMING)
            
        elif self.state == MissionState.RESUMING:
            # Resume from where we left off
            # Load coverage map state
            # Continue path execution
            self.transition_to(MissionState.MOWING)
            
        # Publish current state
        self.state_pub.publish(String(data=self.state.name))
    
    def command_callback(self, msg):
        """Handle mission commands"""
        cmd = msg.data.upper()
        
        if cmd == 'START':
            if self.state == MissionState.IDLE:
                self.transition_to(MissionState.PLANNING)
                
        elif cmd == 'PAUSE':
            if self.state == MissionState.MOWING:
                self.transition_to(MissionState.PAUSED)
                
        elif cmd == 'RESUME':
            if self.state == MissionState.PAUSED:
                self.transition_to(MissionState.MOWING)
                
        elif cmd == 'STOP':
            self.transition_to(MissionState.IDLE)
            
        elif cmd == 'RETURN_TO_DOCK':
            self.transition_to(MissionState.RETURNING_TO_DOCK)
            
        elif cmd == 'EMERGENCY_DOCK':
            # Immediately abort and dock
            self.transition_to(MissionState.RETURNING_TO_DOCK)
    
    def battery_callback(self, msg):
        """Handle battery state changes"""
        battery_state = msg.data
        
        if battery_state == 'LOW' and self.state == MissionState.MOWING:
            self.get_logger().warn('Low battery detected, returning to dock')
            self.transition_to(MissionState.RETURNING_TO_DOCK)
            
        elif battery_state == 'CRITICAL':
            self.get_logger().error('CRITICAL battery! Emergency dock!')
            self.transition_to(MissionState.RETURNING_TO_DOCK)
    
    def transition_to(self, new_state):
        """Transition to new state with logging"""
        old_state = self.state
        self.state = new_state
        self.get_logger().info(f'State transition: {old_state.name} → {new_state.name}')
```

**Mission Manager Topics:**
- `/mission/state` (String): Current state
- `/mission/command` (String): START | PAUSE | RESUME | STOP | RETURN_TO_DOCK
- `/mission/progress` (Float32): 0-100% completion

---

### **PHASE C: Dock Detection & Charging (Week 5-6) - MEDIUM Priority 🟡**

#### C1. AprilTag Detection

**Install apriltag_ros**:
```dockerfile
# In Dockerfile
RUN apt-get update && apt-get install -y \
    ros-humble-apriltag-ros \
    ros-humble-apriltag-msgs \
    && rm -rf /var/lib/apt/lists/*
```

**Configuration** (`config/apriltag_detector.yaml`):
```yaml
apriltag_ros:
  ros__parameters:
    tag_family: 'tag36h11'
    tag_size: 0.162  # 162mm tag (adjust to your tag size)
    camera_frame: 'camera_link_optical'
    publish_tf: true
    
    # Tag definitions
    tag_bundles:
      - name: 'charging_dock'
        layout:
          - id: 0
            size: 0.162
            x: 0.0
            y: 0.0
            z: 0.0
```

**Launch** (`launch/apriltag_dock.launch.py`):
```python
def generate_launch_description():
    apriltag_node = Node(
        package='apriltag_ros',
        executable='apriltag_node',
        name='apriltag_detector',
        parameters=[os.path.join(pkg_share, 'config', 'apriltag_detector.yaml')],
        remappings=[
            ('image_rect', '/camera/image_raw'),
            ('camera_info', '/camera/camera_info')
        ]
    )
    
    return LaunchDescription([apriltag_node])
```

**AprilTag publishes:**
- `/apriltag/detections` (apriltag_msgs/AprilTagDetectionArray)
- `/tf` - Transform from camera to tag

---

#### C2. Dock Navigator

**New Node**: `dock_navigator.py`

```python
#!/usr/bin/env python3
"""
Dock Navigator - Precision docking using AprilTag detection
"""

from apriltag_msgs.msg import AprilTagDetectionArray
from geometry_msgs.msg import Twist, PoseStamped
import numpy as np

class DockNavigator(Node):
    def __init__(self):
        super().__init__('dock_navigator')
        
        # Parameters
        self.declare_parameter('dock_tag_id', 0)
        self.declare_parameter('approach_distance', 2.0)  # meters
        self.declare_parameter('final_distance', 0.3)     # meters
        self.declare_parameter('max_angular_vel', 0.5)    # rad/s
        self.declare_parameter('max_linear_vel', 0.2)     # m/s
        
        # State
        self.docking_active = False
        self.tag_detected = False
        self.tag_pose = None
        
        # Subscribers
        self.create_subscription(
            AprilTagDetectionArray,
            '/apriltag/detections',
            self.tag_callback,
            10
        )
        self.create_subscription(
            String,
            '/dock/command',
            self.command_callback,
            10
        )
        
        # Publishers
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.status_pub = self.create_publisher(String, '/dock/status', 10)
        
        # Control loop
        self.create_timer(0.1, self.control_loop)  # 10 Hz
        
    def tag_callback(self, msg):
        """Process AprilTag detections"""
        dock_tag_id = self.get_parameter('dock_tag_id').value
        
        for detection in msg.detections:
            if detection.id[0] == dock_tag_id:
                self.tag_detected = True
                self.tag_pose = detection.pose.pose.pose
                return
        
        self.tag_detected = False
    
    def command_callback(self, msg):
        """Handle dock commands"""
        if msg.data == 'START':
            self.docking_active = True
            self.get_logger().info('Docking sequence initiated')
        elif msg.data == 'ABORT':
            self.docking_active = False
            self.stop_robot()
    
    def control_loop(self):
        """Main docking control"""
        if not self.docking_active:
            return
        
        if not self.tag_detected:
            # Search for tag - rotate slowly
            self.search_for_tag()
            return
        
        # Extract tag position relative to robot
        x = self.tag_pose.position.z  # Forward (camera frame)
        y = -self.tag_pose.position.x  # Lateral (camera frame)
        
        # Simple proportional controller
        angle_error = np.arctan2(y, x)
        distance_error = np.sqrt(x**2 + y**2) - self.final_distance
        
        cmd = Twist()
        
        if abs(angle_error) > 0.1:  # 5 degrees
            # Align first
            cmd.angular.z = np.clip(
                2.0 * angle_error,
                -self.max_angular_vel,
                self.max_angular_vel
            )
        elif distance_error > 0.05:  # 5cm
            # Drive forward
            cmd.linear.x = np.clip(
                0.5 * distance_error,
                0.0,
                self.max_linear_vel
            )
        else:
            # Docked!
            self.get_logger().info('Docking complete!')
            self.stop_robot()
            self.docking_active = False
            self.status_pub.publish(String(data='DOCKED'))
            return
        
        self.cmd_vel_pub.publish(cmd)
    
    def search_for_tag(self):
        """Rotate to find AprilTag"""
        cmd = Twist()
        cmd.angular.z = 0.3  # Slow rotation
        self.cmd_vel_pub.publish(cmd)
        self.status_pub.publish(String(data='SEARCHING'))
    
    def stop_robot(self):
        """Stop all motion"""
        self.cmd_vel_pub.publish(Twist())
```

**Docking Workflow:**
1. Mission manager sends `/dock/command` = 'START'
2. Robot navigates to vicinity of dock (using Nav2 to known GPS coordinate)
3. Dock navigator activates, searches for AprilTag
4. When tag detected, executes precision alignment
5. Approaches until distance < 0.3m
6. Publishes `/dock/status` = 'DOCKED'
7. Battery monitor detects charging current
8. Mission manager transitions to CHARGING state

---

### **PHASE D: Advanced Features (Week 7-8) - MEDIUM Priority 🟡**

#### D1. Obstacle Avoidance & Recovery

**Enhanced Nav2 Configuration**:

`config/nav2_params.yaml` additions:
```yaml
recoveries_server:
  ros__parameters:
    use_sim_time: false
    recovery_plugins: ["spin", "backup", "wait"]
    spin:
      plugin: "nav2_recoveries/Spin"
      simulate_ahead_time: 2.0
    backup:
      plugin: "nav2_recoveries/BackUp"
      simulate_ahead_time: 2.0
    wait:
      plugin: "nav2_recoveries/Wait"

local_costmap:
  local_costmap:
    ros__parameters:
      update_frequency: 5.0
      publish_frequency: 2.0
      global_frame: odom
      robot_base_frame: base_link
      rolling_window: true
      width: 5
      height: 5
      resolution: 0.05
      robot_radius: 0.3  # Adjust to your robot
      
      plugins: ["obstacle_layer", "inflation_layer"]
      
      obstacle_layer:
        plugin: "nav2_costmap_2d::ObstacleLayer"
        enabled: true
        observation_sources: scan
        scan:
          topic: /scan
          max_obstacle_height: 2.0
          clearing: true
          marking: true
          data_type: "LaserScan"
          
      inflation_layer:
        plugin: "nav2_costmap_2d::InflationLayer"
        cost_scaling_factor: 3.0
        inflation_radius: 0.55
```

**Obstacle Memory Node** (`obstacle_memory.py`):
```python
"""
Obstacle Memory - Track persistent obstacles and update zone coverage map
"""

class ObstacleMemory(Node):
    def __init__(self):
        # Track obstacles that persist across scans
        self.persistent_obstacles = []
        
        self.create_subscription(LaserScan, '/scan', self.scan_callback, 10)
        
        # Publishers
        self.obstacle_pub = self.create_publisher(
            MarkerArray, '/obstacles/persistent', 10
        )
        
    def scan_callback(self, msg):
        """Detect and track obstacles"""
        # Cluster nearby points into obstacles
        obstacles = self.cluster_scan_points(msg)
        
        # Update persistent obstacle list
        for obs in obstacles:
            if self.is_new_obstacle(obs):
                self.persistent_obstacles.append({
                    'position': obs,
                    'first_seen': self.get_clock().now(),
                    'times_seen': 1
                })
            else:
                # Increment existing obstacle
                self.update_obstacle(obs)
        
        # Remove obstacles not seen recently
        self.prune_old_obstacles()
        
        # Publish for visualization
        self.publish_obstacles()
```

---

#### D2. Coverage Tracking

**New Node**: `coverage_tracker.py`

```python
"""
Coverage Tracker - Track which areas have been mowed
Uses grid-based occupancy to track coverage
"""

import numpy as np
from nav_msgs.msg import OccupancyGrid

class CoverageTracker(Node):
    def __init__(self):
        super().__init__('coverage_tracker')
        
        # Parameters
        self.declare_parameter('grid_resolution', 0.5)  # meters
        self.declare_parameter('coverage_radius', 0.6)  # robot cutting width
        
        # Coverage grid (0 = uncovered, 100 = covered)
        self.coverage_grid = None
        self.grid_origin = None
        
        # Subscribers
        self.create_subscription(Odometry, '/odom', self.odom_callback, 10)
        self.create_subscription(Zone, '/zone/current', self.zone_callback, 10)
        
        # Publishers
        self.coverage_pub = self.create_publisher(
            OccupancyGrid, '/coverage/map', 10
        )
        self.progress_pub = self.create_publisher(
            Float32, '/coverage/progress', 10
        )
        
    def zone_callback(self, msg):
        """Initialize coverage grid for new zone"""
        # Create grid based on zone bounds
        vertices = [(p.x, p.y) for p in msg.polygon.polygon.points]
        minx = min(v[0] for v in vertices)
        maxx = max(v[0] for v in vertices)
        miny = min(v[1] for v in vertices)
        maxy = max(v[1] for v in vertices)
        
        width = int((maxx - minx) / self.grid_resolution)
        height = int((maxy - miny) / self.grid_resolution)
        
        self.coverage_grid = np.zeros((height, width), dtype=np.uint8)
        self.grid_origin = (minx, miny)
        
        self.get_logger().info(f'Initialized coverage grid: {width}x{height}')
    
    def odom_callback(self, msg):
        """Update coverage based on robot position"""
        if self.coverage_grid is None:
            return
        
        # Get robot position
        x = msg.pose.pose.position.x
        y = msg.pose.pose.position.y
        
        # Convert to grid coordinates
        grid_x = int((x - self.grid_origin[0]) / self.grid_resolution)
        grid_y = int((y - self.grid_origin[1]) / self.grid_resolution)
        
        # Mark coverage in radius around robot
        radius_cells = int(self.coverage_radius / self.grid_resolution)
        
        for dx in range(-radius_cells, radius_cells + 1):
            for dy in range(-radius_cells, radius_cells + 1):
                if dx**2 + dy**2 <= radius_cells**2:
                    gx = grid_x + dx
                    gy = grid_y + dy
                    
                    if (0 <= gx < self.coverage_grid.shape[1] and
                        0 <= gy < self.coverage_grid.shape[0]):
                        self.coverage_grid[gy, gx] = 100  # Covered
        
        # Calculate and publish coverage percentage
        total_cells = self.coverage_grid.size
        covered_cells = np.sum(self.coverage_grid == 100)
        progress = (covered_cells / total_cells) * 100.0
        
        self.progress_pub.publish(Float32(data=progress))
        
        # Publish coverage grid for visualization
        self.publish_coverage_grid()
```

---

## 📦 IMPLEMENTATION PACKAGES

### New Package Structure

```
src/
├── rosmower/                      # Existing - add new nodes
│   ├── scripts/
│   │   ├── mission_manager.py     # NEW
│   │   ├── battery_monitor.py     # NEW
│   │   ├── zone_manager.py        # NEW
│   │   ├── random_path_generator.py  # NEW
│   │   ├── dock_navigator.py      # NEW
│   │   ├── coverage_tracker.py    # NEW
│   │   └── obstacle_memory.py     # NEW
│   ├── config/
│   │   ├── battery_manager.yaml   # NEW
│   │   ├── apriltag_detector.yaml # NEW
│   │   └── coverage_planner.yaml  # NEW
│   └── web/
│       └── zone_manager.html      # NEW
│
├── rosmower_msgs/                 # NEW PACKAGE - Custom messages
│   ├── msg/
│   │   ├── Zone.msg
│   │   ├── ZoneArray.msg
│   │   ├── MissionState.msg
│   │   └── CoverageProgress.msg
│   ├── srv/
│   │   ├── SaveZone.srv
│   │   ├── LoadZone.srv
│   │   └── ListZones.srv
│   └── package.xml
│
└── zones/                         # NEW - Zone storage
    ├── front_yard.yaml
    ├── back_yard.yaml
    └── zones_index.yaml
```

---

## 🔧 DOCKER UPDATES

### Dockerfile Additions

```dockerfile
# Add coverage planning and AprilTag detection
RUN apt-get update && apt-get install -y \
    ros-${ROS_DISTRO}-apriltag-ros \
    ros-${ROS_DISTRO}-apriltag-msgs \
    ros-${ROS_DISTRO}-nav2-waypoint-follower \
    ros-${ROS_DISTRO}-nav2-lifecycle-manager \
    python3-shapely \
    python3-pyproj \
    python3-pillow \
    && rm -rf /var/lib/apt/lists/*
```

---

## 🎯 INTEGRATION ROADMAP

### **Sprint 1 (Week 1-2): Foundation**
- ✅ Implement battery_monitor.py
- ✅ Implement zone_manager.py
- ✅ Create rosmower_msgs package
- ✅ Build basic web UI for zone drawing
- ✅ Test battery alerts and zone storage

**Deliverable**: Can define zones via web UI, battery monitor triggers alerts

---

### **Sprint 2 (Week 3-4): Path Planning**
- ✅ Implement random_path_generator.py
- ✅ Implement mission_manager.py (basic state machine)
- ✅ Integrate with Nav2 waypoint follower
- ✅ Test path generation and navigation within zone

**Deliverable**: Robot can autonomously follow generated path in zone

---

### **Sprint 3 (Week 5-6): Dock & Charge**
- ✅ Install AprilTag on charging dock
- ✅ Configure apriltag_ros
- ✅ Implement dock_navigator.py
- ✅ Test dock detection and alignment
- ✅ Integrate with battery_monitor for charge detection

**Deliverable**: Robot can autonomously dock and charge

---

### **Sprint 4 (Week 7-8): Coverage & Recovery**
- ✅ Implement coverage_tracker.py
- ✅ Implement obstacle_memory.py
- ✅ Configure Nav2 recovery behaviors
- ✅ Test full mission: zone → path → mow → low battery → dock → charge → resume

**Deliverable**: Fully autonomous multi-zone mowing with resume capability

---

### **Sprint 5 (Week 9-10): Polish & Edge Cases**
- ✅ GPS drift compensation
- ✅ Zone transition planning
- ✅ Enhanced web UI with live map
- ✅ Mission scheduling (time-based, weather-aware)
- ✅ Error recovery and fault tolerance

**Deliverable**: Production-ready autonomous mower

---

## 📊 UPDATED ARCHITECTURE DIAGRAM

```
┌─────────────────────────────────────────────────────────────────┐
│                      MISSION PLANNING LAYER                      │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Mission    │◄─┤    Zone      │  │   Battery    │          │
│  │   Manager    │  │   Manager    │  │   Monitor    │          │
│  │              │  │              │  │              │          │
│  │ State:MOWING │  │ Load zones   │  │ 78% NORMAL   │          │
│  └──────┬───────┘  └──────────────┘  └──────┬───────┘          │
│         │ /mission/state                    │ /battery/low     │
│         │                                    │                  │
└─────────┼────────────────────────────────────┼──────────────────┘
          │                                    │
          ▼ /path/generate                    ▼ RETURN_TO_DOCK
┌─────────────────────────────────────────────────────────────────┐
│                    NAVIGATION & PLANNING LAYER                   │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Coverage    │  │    Nav2      │  │    Dock      │          │
│  │  Path        │─►│   Stack      │  │  Navigator   │          │
│  │  Generator   │  │              │  │              │          │
│  │              │  │ Waypoint     │  │ AprilTag     │          │
│  │ Boustrophedon│  │ Follower     │  │ Align        │          │
│  └──────────────┘  └──────┬───────┘  └──────────────┘          │
│                           │ /cmd_vel                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Coverage    │  │  Obstacle    │  │  Costmap     │          │
│  │  Tracker     │  │  Memory      │  │  (Nav2)      │          │
│  │              │  │              │  │              │          │
│  │ 45% done     │  │ 3 persistent │  │ Inflation    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────┬───────────────────────┘
                                          │
                                          ▼ Twist commands
┌─────────────────────────────────────────────────────────────────┐
│                      HARDWARE CONTROL LAYER                      │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Hoverboard  │  │     EKF      │  │   LiDAR      │          │
│  │   Bridge     │  │  Localization│  │   RPLiDAR    │          │
│  │              │  │              │  │              │          │
│  │ Wheel Odom   │  │ Fused Pose   │  │ /scan        │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   RTK GPS    │  │     IMU      │  │   Camera     │          │
│  │   LC29HDA    │  │  ICM20948    │  │   IMX219     │          │
│  │              │  │              │  │              │          │
│  │ 2cm accuracy │  │ 9-DOF        │  │ AprilTag     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🌐 ENHANCED WEB UI FEATURES

### Zone Manager Interface
- **Interactive map** with satellite imagery (Leaflet.js)
- **Draw polygon zones** with mouse/touch
- **Edit existing zones** (move vertices, resize)
- **Zone properties**: Name, priority, schedule, enabled/disabled
- **Zone preview**: Show coverage overlay

### Mission Dashboard
- **Live robot position** on map
- **Current zone** highlighted
- **Coverage progress** (percentage + heat map)
- **Battery level** with time remaining
- **Mission controls**: START, PAUSE, RESUME, ABORT
- **Status indicators**: GPS fix quality, obstacle count, charging state

### Real-time Monitoring
- **ROS topic monitor** (battery, GPS, scan)
- **Node health** (all nodes running?)
- **Log viewer** (recent errors/warnings)
- **Camera feed** (live MJPEG stream)

---

## ⚠️ CRITICAL CONSIDERATIONS

### 1. **GPS Drift & Fence Handling**
**Problem**: RTK GPS can drift 2-10cm, fence detection may be unreliable

**Solution**:
- Use **boundary inflation** (shrink zone by 0.5m for safety)
- Implement **geofence monitoring node**:
  ```python
  def check_geofence(self, current_pos, zone):
      if not zone.polygon.contains(current_pos):
          self.get_logger().warn('Robot outside zone!')
          self.mission_manager_pub.publish(String(data='STOP'))
  ```
- **Fallback to LiDAR**: If GPS quality drops, use costmap boundaries

### 2. **Battery Degradation**