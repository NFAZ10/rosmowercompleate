# 🚀 AUTONOMOUS MOWER - IMPLEMENTATION CHECKLIST

**Quick Reference Guide for Incremental Development**

---

## ✅ PHASE A: FOUNDATION (Week 1-2) - HIGH PRIORITY

### [ ] 1. Create Custom Messages Package (30 min)

```bash
cd /mnt/nova_ssd/rosmowercompleate/src
ros2 pkg create rosmower_msgs --build-type ament_cmake
mkdir -p rosmower_msgs/msg rosmower_msgs/srv
```

**Message Definitions:**

`msg/Zone.msg`:
```
string id
string name
uint8 priority
geometry_msgs/PolygonStamped polygon
bool enabled
float64 coverage_percent
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

`srv/LoadZone.srv`:
```
string zone_id
---
bool success
Zone zone
```

`srv/ListZones.srv`:
```
---
string[] zone_ids
ZoneArray zones
```

**Update CMakeLists.txt and package.xml, then build:**
```bash
cd /mnt/nova_ssd/rosmowercompleate
colcon build --packages-select rosmower_msgs
source install/setup.bash
```

---

### [ ] 2. Implement Battery Monitor (2 hours)

**File**: `src/rosmower/scripts/battery_monitor.py`

**Key Features:**
- Subscribe to `/percent` (Float32) and `/current` (Float32)
- Publish `/battery/state` (String): NORMAL | LOW | CRITICAL | CHARGING | CHARGED
- Publish `/battery/low` (Bool)
- Publish `/mission/command` (String): RETURN_TO_DOCK | EMERGENCY_DOCK
- Parameters: low_threshold (25%), critical_threshold (15%), charged_threshold (95%)

**Config**: `config/battery_manager.yaml`

**Test**:
```bash
# Terminal 1: Launch robot
./docker-helper.sh exec ros2 launch rosmower launch_robot.launch.py

# Terminal 2: Run battery monitor
./docker-helper.sh exec ros2 run rosmower battery_monitor.py

# Terminal 3: Simulate battery drain
./docker-helper.sh exec ros2 topic pub /percent std_msgs/Float32 "data: 20.0"

# Check alert triggered
./docker-helper.sh exec ros2 topic echo /battery/state
./docker-helper.sh exec ros2 topic echo /mission/command
```

---

### [ ] 3. Implement Zone Manager (4 hours)

**File**: `src/rosmower/scripts/zone_manager.py`

**Key Features:**
- Load zones from `/ws/zones/*.yaml`
- Services: `/zone/save`, `/zone/load`, `/zone/list`
- Publishers: `/zones` (ZoneArray), `/zone/current` (Zone)
- GPS ↔ Map coordinate conversion (pyproj)

**Dependencies**:
```bash
# Add to Dockerfile
RUN apt-get update && apt-get install -y \
    python3-shapely \
    python3-pyproj \
    && rm -rf /var/lib/apt/lists/*
```

**Directory Setup**:
```bash
mkdir -p /ws/zones
```

**Sample Zone** (`/ws/zones/front_yard.yaml`):
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

**Test**:
```bash
# Launch zone manager
./docker-helper.sh exec ros2 run rosmower zone_manager.py

# List zones
./docker-helper.sh exec ros2 service call /zone/list rosmower_msgs/srv/ListZones

# Load zone
./docker-helper.sh exec ros2 service call /zone/load rosmower_msgs/srv/LoadZone "zone_id: 'front_yard'"

# Check published zones
./docker-helper.sh exec ros2 topic echo /zones
```

---

### [ ] 4. Build Web UI - Zone Drawing (4 hours)

**File**: `src/rosmower/web/zone_manager.html`

**Features:**
- Leaflet.js map with satellite imagery
- Leaflet-Draw for polygon drawing
- Connect to /api/zones endpoints
- Zone list panel with priority editing

**Backend** (`web_server.py` additions):
```python
@app.route('/api/zones')
def get_zones():
    # Call ROS2 service /zone/list
    result = call_service('rosmower_msgs/srv/ListZones', '/zone/list', {})
    return jsonify(result)

@app.route('/api/zones/save', methods=['POST'])
def save_zone():
    zone_data = request.json
    result = call_service('rosmower_msgs/srv/SaveZone', '/zone/save', zone_data)
    return jsonify(result)
```

**Test**:
```bash
# Start web server
./start-web-server.sh

# Open browser: http://<robot-ip>:8080/zone_manager.html
# Draw polygon
# Save zone
# Verify YAML file created in /ws/zones/
```

---

## ✅ PHASE B: PATH PLANNING (Week 3-4) - HIGH PRIORITY

### [ ] 5. Implement Path Generator (4 hours)

**File**: `src/rosmower/scripts/random_path_generator.py`

**Two Options:**

**Option A: Random Waypoints (Simple MVP)**
- Generate random points within zone polygon
- Use Shapely for point-in-polygon checks

**Option B: Boustrophedon Pattern (Recommended)**
- Back-and-forth lawn mower pattern
- Configurable spacing (2m)
- Follows zone boundaries

**Key Features:**
- Subscribe to `/zone/current` (Zone)
- Publish `/path/coverage` (nav_msgs/Path)
- Service `/path/generate` (std_srvs/Trigger)
- Parameters: waypoint_spacing, num_waypoints (for random)

**Test**:
```bash
# Launch path generator
./docker-helper.sh exec ros2 run rosmower random_path_generator.py

# Set current zone
./docker-helper.sh exec ros2 topic pub /zone/current rosmower_msgs/Zone "..."

# Generate path
./docker-helper.sh exec ros2 service call /path/generate std_srvs/srv/Trigger

# Visualize in RViz
./docker-helper.sh exec ros2 topic echo /path/coverage
```

---

### [ ] 6. Implement Mission Manager (6 hours)

**File**: `src/rosmower/scripts/mission_manager.py`

**State Machine:**
```
IDLE → PLANNING → MOWING → PAUSED
                  ↓
         RETURNING_TO_DOCK → DOCKING → CHARGING → RESUMING
                  ↓
              COMPLETE / ERROR
```

**Key Features:**
- Subscribe: `/mission/command`, `/battery/state`, `/zone/current`
- Publish: `/mission/state`, `/goal_pose` (for Nav2)
- Integrate: zone_manager, path_generator, Nav2
- Timer callback for state machine (0.5 Hz)

**Commands:**
- START, PAUSE, RESUME, STOP, RETURN_TO_DOCK

**Test**:
```bash
# Launch full stack
./docker-helper.sh exec ros2 launch rosmower launch_robot.launch.py
./docker-helper.sh exec ros2 run rosmower battery_monitor.py
./docker-helper.sh exec ros2 run rosmower zone_manager.py
./docker-helper.sh exec ros2 run rosmower mission_manager.py

# Start mission
./docker-helper.sh exec ros2 topic pub /mission/command std_msgs/String "data: 'START'"

# Monitor state
./docker-helper.sh exec ros2 topic echo /mission/state
```

---

### [ ] 7. Integrate Nav2 Waypoint Follower (2 hours)

**Update** `launch_robot.launch.py`:
```python
# Add Nav2 waypoint follower
waypoint_follower = Node(
    package='nav2_waypoint_follower',
    executable='waypoint_follower',
    name='waypoint_follower',
    parameters=[nav2_params_file]
)
```

**Config** (`config/nav2_params.yaml`):
```yaml
waypoint_follower:
  ros__parameters:
    loop_rate: 20
    stop_on_failure: true
    waypoint_task_executor_plugin: "wait_at_waypoint"
```

**Test**:
```bash
# Generate path
ros2 service call /path/generate std_srvs/srv/Trigger

# Nav2 should automatically follow path published to /path/coverage
# Monitor progress
ros2 topic echo /odom
```

---

## ✅ PHASE C: DOCK & CHARGE (Week 5-6) - MEDIUM PRIORITY

### [ ] 8. Install AprilTag Detection (2 hours)

**Update Dockerfile**:
```dockerfile
RUN apt-get update && apt-get install -y \
    ros-humble-apriltag-ros \
    ros-humble-apriltag-msgs \
    && rm -rf /var/lib/apt/lists/*
```

**Config** (`config/apriltag_detector.yaml`):
```yaml
apriltag_ros:
  ros__parameters:
    tag_family: 'tag36h11'
    tag_size: 0.162  # 162mm (6.4 inches)
    camera_frame: 'camera_link_optical'
    publish_tf: true
    tag_bundles:
      - name: 'charging_dock'
        layout:
          - id: 0
            size: 0.162
```

**Launch** (`launch/apriltag_dock.launch.py`):
```python
apriltag_node = Node(
    package='apriltag_ros',
    executable='apriltag_node',
    parameters=[apriltag_config],
    remappings=[
        ('image_rect', '/camera/image_raw'),
        ('camera_info', '/camera/camera_info')
    ]
)
```

**Hardware Setup:**
- Print AprilTag (tag36h11, ID 0, 162mm size)
- Mount on charging dock at camera height
- Ensure good lighting

**Test**:
```bash
# Launch AprilTag detector
./docker-helper.sh exec ros2 launch rosmower apriltag_dock.launch.py

# Point camera at tag
./docker-helper.sh exec ros2 topic echo /apriltag/detections

# Should see detection with pose
```

---

### [ ] 9. Implement Dock Navigator (4 hours)

**File**: `src/rosmower/scripts/dock_navigator.py`

**Key Features:**
- Subscribe: `/apriltag/detections`
- Publish: `/cmd_vel`, `/dock/status` (SEARCHING | ALIGNING | DOCKED)
- Command: `/dock/command` (START | ABORT)
- Proportional controller for alignment and approach

**Docking Algorithm:**
1. If tag not visible: rotate slowly (search)
2. If tag visible but misaligned: rotate to center
3. If aligned but distant: drive forward
4. If aligned and close (<0.3m): stop, publish DOCKED

**Test**:
```bash
# Launch dock navigator
./docker-helper.sh exec ros2 run rosmower dock_navigator.py

# Place robot 2m from dock, AprilTag visible
# Start docking
./docker-helper.sh exec ros2 topic pub /dock/command std_msgs/String "data: 'START'"

# Monitor status
./docker-helper.sh exec ros2 topic echo /dock/status
./docker-helper.sh exec ros2 topic echo /cmd_vel

# Robot should align and approach
```

---

### [ ] 10. Integrate Charging Detection (1 hour)

**Update** `battery_monitor.py`:
```python
def current_callback(self, msg):
    self.current = msg.data
    
    # Detect charging
    if self.current < -0.1:  # Negative = charging
        if self.state != 'CHARGING':
            self.transition_to('CHARGING')
```

**Test**:
```bash
# Simulate charging current
./docker-helper.sh exec ros2 topic pub /current std_msgs/Float32 "data: -1.5"

# Check state transition
./docker-helper.sh exec ros2 topic echo /battery/state
# Should show "CHARGING"
```

---

## ✅ PHASE D: ADVANCED FEATURES (Week 7-8) - MEDIUM PRIORITY

### [ ] 11. Implement Coverage Tracker (4 hours)

**File**: `src/rosmower/scripts/coverage_tracker.py`

**Key Features:**
- Grid-based occupancy (0=uncovered, 100=covered)
- Subscribe: `/odom`, `/zone/current`
- Publish: `/coverage/map` (OccupancyGrid), `/coverage/progress` (Float32)
- Save/load coverage state for resume

**Test**:
```bash
# Launch coverage tracker
./docker-helper.sh exec ros2 run rosmower coverage_tracker.py

# Set zone
ros2 topic pub /zone/current rosmower_msgs/Zone "..."

# Drive robot around
# Monitor coverage progress
ros2 topic echo /coverage/progress
```

---

### [ ] 12. Implement Obstacle Memory (3 hours)

**File**: `src/rosmower/scripts/obstacle_memory.py`

**Key Features:**
- Track obstacles seen repeatedly
- Publish `/obstacles/persistent` (MarkerArray)
- Integration with path planner to avoid persistent obstacles

---

### [ ] 13. Configure Nav2 Recovery Behaviors (2 hours)

**Update** `config/nav2_params.yaml`:
- Enable spin, backup, wait recoveries
- Configure obstacle_layer in costmap
- Set inflation radius

**Test obstacle avoidance:**
```bash
# Place obstacle in robot path
# Nav2 should automatically avoid or trigger recovery
```

---

## ✅ PHASE E: POLISH (Week 9-10) - LOW PRIORITY

### [ ] 14. Enhanced Web UI
- [ ] Live robot position on map
- [ ] Coverage heat map overlay
- [ ] Mission progress dashboard
- [ ] Real-time battery gauge

### [ ] 15. GPS Drift Compensation
- [ ] Geofence monitoring node
- [ ] Boundary inflation (0.5m safety)
- [ ] GPS quality monitoring

### [ ] 16. Multi-Zone Scheduling
- [ ] Zone priority sequencing
- [ ] Time-based scheduling
- [ ] Battery-aware zone selection

---

## 🧪 END-TO-END TEST SCENARIOS

### Test 1: Single Zone Coverage
1. Define zone via web UI
2. Start mission
3. Verify path generated
4. Verify robot follows path
5. Check coverage progress
6. Verify completion detection

### Test 2: Low Battery Dock Return
1. Start mission with battery at 30%
2. Manually lower battery to 24%
3. Verify mission manager triggers RETURN_TO_DOCK
4. Verify Nav2 navigates to dock GPS
5. Verify dock navigator takes over
6. Verify docking success
7. Verify charging detection

### Test 3: Resume After Charge
1. Start mission
2. Trigger low battery mid-zone
3. Complete docking and charging
4. Verify battery reaches 95%
5. Verify mission resumes
6. Check coverage state restored
7. Verify robot continues from where it left off

### Test 4: Obstacle Avoidance
1. Place obstacle in path
2. Verify LiDAR detects obstacle
3. Verify Nav2 replans around obstacle
4. Verify mission continues

### Test 5: Multi-Zone Mission
1. Define 2+ zones with different priorities
2. Start mission
3. Verify zones executed in priority order
4. Verify zone transitions

---

## 📊 METRICS TO TRACK

- [ ] Zone definition success rate (web UI usability)
- [ ] Path generation time (should be <5 seconds)
- [ ] Nav2 goal success rate (>95%)
- [ ] Docking success rate (>90%)
- [ ] Charging detection time (<10 seconds)
- [ ] Resume accuracy (overlap <5%)
- [ ] Mission completion time vs. estimate
- [ ] Battery prediction accuracy

---

## 🔧 DEBUGGING TIPS

### Check Node Status
```bash
ros2 node list
ros2 node info /mission_manager
```

### Monitor Topics
```bash
ros2 topic list
ros2 topic echo /mission/state
ros2 topic hz /scan
```

### Check Services
```bash
ros2 service list
ros2 service type /zone/save
```

### View in RViz
```bash
ros2 launch rosmower rviz.launch.py
# Add displays: /scan, /path/coverage, /coverage/map, /zones
```

### Check Logs
```bash
ros2 run rqt_console rqt_console
# Filter by node: mission_manager
```

---

## 🎯 COMPLETION CRITERIA

**Phase A Complete When:**
- ✅ 3+ zones defined and persisting
- ✅ Battery alerts triggering correctly
- ✅ Web UI functional for zone management

**Phase B Complete When:**
- ✅ Path generated within zones
- ✅ Robot follows paths autonomously
- ✅ Mission state machine working

**Phase C Complete When:**
- ✅ AprilTag detected reliably
- ✅ Docking success >90%
- ✅ Charging detected automatically

**Phase D Complete When:**
- ✅ Coverage tracked accurately
- ✅ Obstacles avoided automatically
- ✅ Resume after charge working

**Phase E Complete When:**
- ✅ Multi-zone missions complete unattended
- ✅ GPS drift handled gracefully
- ✅ Web UI shows real-time status

---

**READY TO START? Begin with Phase A, Task 1: Create rosmower_msgs package!**
