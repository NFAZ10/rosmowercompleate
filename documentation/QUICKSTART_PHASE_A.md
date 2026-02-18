# 🚀 QUICK START: Phase A - Foundation

**Goal**: Implement zone management and battery monitoring in 1-2 weeks

---

## 📋 Prerequisites

- ROS2 Humble installed (✓ already have)
- Docker environment running (✓ already have)
- Basic Python knowledge
- 8-16 hours of development time

---

## ⚡ Task 1: Create rosmower_msgs Package (30 minutes)

### Step 1.1: Create Package Structure

```bash
cd /mnt/nova_ssd/rosmowercompleate/src
ros2 pkg create rosmower_msgs --build-type ament_cmake
cd rosmower_msgs
mkdir msg srv
```

### Step 1.2: Define Zone Message

Create `msg/Zone.msg`:
```bash
cat > msg/Zone.msg << 'EOF'
string id
string name
uint8 priority
geometry_msgs/PolygonStamped polygon
bool enabled
float64 coverage_percent
EOF
```

### Step 1.3: Define ZoneArray Message

Create `msg/ZoneArray.msg`:
```bash
cat > msg/ZoneArray.msg << 'EOF'
std_msgs/Header header
Zone[] zones
EOF
```

### Step 1.4: Define Services

Create `srv/SaveZone.srv`:
```bash
cat > srv/SaveZone.srv << 'EOF'
Zone zone
---
bool success
string message
EOF
```

Create `srv/LoadZone.srv`:
```bash
cat > srv/LoadZone.srv << 'EOF'
string zone_id
---
bool success
Zone zone
EOF
```

Create `srv/ListZones.srv`:
```bash
cat > srv/ListZones.srv << 'EOF'
---
string[] zone_ids
ZoneArray zones
EOF
```

### Step 1.5: Update CMakeLists.txt

Edit `CMakeLists.txt`:
```cmake
cmake_minimum_required(VERSION 3.8)
project(rosmower_msgs)

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(rosidl_default_generators REQUIRED)

# Generate messages and services
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/Zone.msg"
  "msg/ZoneArray.msg"
  "srv/SaveZone.srv"
  "srv/LoadZone.srv"
  "srv/ListZones.srv"
  DEPENDENCIES std_msgs geometry_msgs
)

ament_package()
```

### Step 1.6: Update package.xml

Edit `package.xml`:
```xml
<?xml version="1.0"?>
<?xml-model href="http://download.ros.org/schema/package_format3.xsd" schematypens="http://www.w3.org/2001/XMLSchema"?>
<package format="3">
  <name>rosmower_msgs</name>
  <version>0.0.1</version>
  <description>Custom messages for rosmower</description>
  <maintainer email="you@example.com">Your Name</maintainer>
  <license>MIT</license>

  <buildtool_depend>ament_cmake</buildtool_depend>
  
  <depend>std_msgs</depend>
  <depend>geometry_msgs</depend>
  
  <build_depend>rosidl_default_generators</build_depend>
  <exec_depend>rosidl_default_runtime</exec_depend>
  <member_of_group>rosidl_interface_packages</member_of_group>

  <export>
    <build_type>ament_cmake</build_type>
  </export>
</package>
```

### Step 1.7: Build Package

```bash
cd /mnt/nova_ssd/rosmowercompleate
colcon build --packages-select rosmower_msgs
source install/setup.bash
```

### Step 1.8: Verify

```bash
# Check messages
ros2 interface show rosmower_msgs/msg/Zone
ros2 interface show rosmower_msgs/srv/SaveZone

# Should see your message definitions
```

✅ **Checkpoint**: Messages and services are now available to use!

---

## ⚡ Task 2: Implement Battery Monitor (2 hours)

### Step 2.1: Create Node File

```bash
cd /mnt/nova_ssd/rosmowercompleate/src/rosmower/scripts
cat > battery_monitor.py << 'ENDOFFILE'
#!/usr/bin/env python3
"""
Battery Monitor Node
Monitors battery percentage and current, triggers dock return when low
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, String, Bool

class BatteryState:
    NORMAL = "NORMAL"
    LOW = "LOW"
    CRITICAL = "CRITICAL"
    CHARGING = "CHARGING"
    CHARGED = "CHARGED"

class BatteryMonitor(Node):
    def __init__(self):
        super().__init__('battery_monitor')
        
        # Declare parameters
        self.declare_parameter('low_battery_threshold', 25.0)
        self.declare_parameter('critical_battery_threshold', 15.0)
        self.declare_parameter('charged_threshold', 95.0)
        self.declare_parameter('charging_current_threshold', -0.1)
        
        # Get parameters
        self.low_threshold = self.get_parameter('low_battery_threshold').value
        self.critical_threshold = self.get_parameter('critical_battery_threshold').value
        self.charged_threshold = self.get_parameter('charged_threshold').value
        self.charging_current = self.get_parameter('charging_current_threshold').value
        
        # State variables
        self.battery_percent = 100.0
        self.current = 0.0
        self.state = BatteryState.NORMAL
        
        # Subscribers
        self.create_subscription(Float32, '/percent', self.battery_callback, 10)
        self.create_subscription(Float32, '/current', self.current_callback, 10)
        
        # Publishers
        self.state_pub = self.create_publisher(String, '/battery/state', 10)
        self.low_battery_pub = self.create_publisher(Bool, '/battery/low', 10)
        self.mission_cmd_pub = self.create_publisher(String, '/mission/command', 10)
        
        # Timer for periodic state updates
        self.create_timer(1.0, self.update_state)
        
        self.get_logger().info('Battery Monitor started')
        self.get_logger().info(f'Low: {self.low_threshold}%, Critical: {self.critical_threshold}%')
        
    def battery_callback(self, msg):
        self.battery_percent = msg.data
        
    def current_callback(self, msg):
        self.current = msg.data
        
    def update_state(self):
        """Update battery state based on percentage and current"""
        old_state = self.state
        
        # Check if charging (negative current)
        if self.current < self.charging_current:
            if self.battery_percent >= self.charged_threshold:
                self.state = BatteryState.CHARGED
            else:
                self.state = BatteryState.CHARGING
        # Check battery level
        elif self.battery_percent < self.critical_threshold:
            self.state = BatteryState.CRITICAL
        elif self.battery_percent < self.low_threshold:
            self.state = BatteryState.LOW
        else:
            self.state = BatteryState.NORMAL
        
        # State transition logic
        if old_state != self.state:
            self.get_logger().info(f'Battery state changed: {old_state} -> {self.state}')
            
            # Trigger mission commands on critical transitions
            if self.state == BatteryState.CRITICAL and old_state != BatteryState.CHARGING:
                self.get_logger().error('CRITICAL BATTERY! Emergency dock!')
                cmd = String()
                cmd.data = 'EMERGENCY_DOCK'
                self.mission_cmd_pub.publish(cmd)
                
            elif self.state == BatteryState.LOW and old_state == BatteryState.NORMAL:
                self.get_logger().warn('Low battery detected, should return to dock')
                cmd = String()
                cmd.data = 'RETURN_TO_DOCK'
                self.mission_cmd_pub.publish(cmd)
                
            elif self.state == BatteryState.CHARGED and old_state == BatteryState.CHARGING:
                self.get_logger().info('Battery fully charged, ready to resume')
                cmd = String()
                cmd.data = 'BATTERY_CHARGED'
                self.mission_cmd_pub.publish(cmd)
        
        # Publish current state
        state_msg = String()
        state_msg.data = self.state
        self.state_pub.publish(state_msg)
        
        # Publish low battery flag
        low_msg = Bool()
        low_msg.data = (self.state in [BatteryState.LOW, BatteryState.CRITICAL])
        self.low_battery_pub.publish(low_msg)
        
        # Log status periodically (every 10 seconds)
        if self.get_clock().now().nanoseconds % 10000000000 < 1000000000:
            self.get_logger().info(
                f'Battery: {self.battery_percent:.1f}%, '
                f'Current: {self.current:.2f}A, '
                f'State: {self.state}'
            )

def main(args=None):
    rclpy.init(args=args)
    node = BatteryMonitor()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
ENDOFFILE

chmod +x battery_monitor.py
```

### Step 2.2: Create Config File

```bash
cd /mnt/nova_ssd/rosmowercompleate/src/rosmower/config
cat > battery_manager.yaml << 'EOF'
battery_monitor:
  ros__parameters:
    low_battery_threshold: 25.0      # Percent - start return to dock
    critical_battery_threshold: 15.0  # Percent - emergency dock NOW
    charged_threshold: 95.0           # Percent - consider fully charged
    charging_current_threshold: -0.1  # Amperes - negative = charging
EOF
```

### Step 2.3: Update package.xml

Edit `src/rosmower/package.xml` to add dependency:
```xml
<exec_depend>rclpy</exec_depend>
<exec_depend>std_msgs</exec_depend>
```

### Step 2.4: Update setup.py

Edit `src/rosmower/setup.py` to install the script:
```python
entry_points={
    'console_scripts': [
        # ... existing entries ...
        'battery_monitor = rosmower.battery_monitor:main',
    ],
},
```

### Step 2.5: Test Battery Monitor

```bash
# Terminal 1: Launch robot (if not already running)
cd /mnt/nova_ssd/rosmowercompleate
./docker-helper.sh exec ros2 launch rosmower launch_robot.launch.py

# Terminal 2: Run battery monitor
./docker-helper.sh exec ros2 run rosmower battery_monitor.py

# Terminal 3: Monitor topics
./docker-helper.sh exec ros2 topic echo /battery/state

# Terminal 4: Simulate battery drain
./docker-helper.sh exec ros2 topic pub /percent std_msgs/Float32 "data: 100.0"
# Wait, then
./docker-helper.sh exec ros2 topic pub /percent std_msgs/Float32 "data: 24.0"
# Should see LOW state and RETURN_TO_DOCK command

# Simulate critical
./docker-helper.sh exec ros2 topic pub /percent std_msgs/Float32 "data: 14.0"
# Should see CRITICAL state and EMERGENCY_DOCK command

# Simulate charging
./docker-helper.sh exec ros2 topic pub /current std_msgs/Float32 "data: -1.5"
./docker-helper.sh exec ros2 topic pub /percent std_msgs/Float32 "data: 96.0"
# Should see CHARGED state
```

✅ **Checkpoint**: Battery monitor responds to battery changes and triggers mission commands!

---

## ⚡ Task 3: Implement Zone Manager (4 hours)

### Step 3.1: Install Dependencies

Update `Dockerfile` to add:
```dockerfile
RUN apt-get update && apt-get install -y \
    python3-shapely \
    python3-pyproj \
    python3-yaml \
    && rm -rf /var/lib/apt/lists/*
```

Rebuild Docker:
```bash
cd /mnt/nova_ssd/rosmowercompleate
docker compose build
```

### Step 3.2: Create Zones Directory

```bash
mkdir -p /mnt/nova_ssd/rosmowercompleate/zones
```

### Step 3.3: Create Zone Manager Node

```bash
cd /mnt/nova_ssd/rosmowercompleate/src/rosmower/scripts
# This is a longer file - see IMPLEMENTATION_CHECKLIST.md for full code
# Or I can provide it in next message if needed
```

**Key features to implement:**
- Load zones from `/ws/zones/*.yaml`
- Implement SaveZone, LoadZone, ListZones services
- GPS <-> Map coordinate conversion using pyproj
- Publish `/zones` and `/zone/current`

### Step 3.4: Create Sample Zone

```bash
cat > /mnt/nova_ssd/rosmowercompleate/zones/test_zone.yaml << 'EOF'
id: "test_zone"
name: "Test Zone"
priority: 5
frame_id: "map"
vertices:
  - {x: 0.0, y: 0.0}
  - {x: 10.0, y: 0.0}
  - {x: 10.0, y: 10.0}
  - {x: 0.0, y: 10.0}
enabled: true
coverage_percent: 0.0
EOF
```

### Step 3.5: Test Zone Manager

```bash
# Launch zone manager
./docker-helper.sh exec ros2 run rosmower zone_manager.py

# List zones
./docker-helper.sh exec ros2 service call /zone/list rosmower_msgs/srv/ListZones

# Load a zone
./docker-helper.sh exec ros2 service call /zone/load rosmower_msgs/srv/LoadZone "zone_id: 'test_zone'"

# Check published zones
./docker-helper.sh exec ros2 topic echo /zones --once
```

✅ **Checkpoint**: Zone manager loads zones and provides services!

---

## ⚡ Task 4: Web UI - Zone Drawing (4 hours)

### Step 4.1: Create Zone Manager HTML

```bash
cd /mnt/nova_ssd/rosmowercompleate/src/rosmower/web
# Create zone_manager.html
# See IMPLEMENTATION_CHECKLIST.md for full HTML code
```

### Step 4.2: Update Web Server

Edit `web_server.py` to add endpoints:
```python
@app.route('/zone_manager')
def zone_manager():
    return send_from_directory('/path/to/web', 'zone_manager.html')

@app.route('/api/zones', methods=['GET'])
def get_zones():
    # Call ROS2 service /zone/list
    # Return JSON
    pass

@app.route('/api/zones/save', methods=['POST'])
def save_zone():
    # Get zone data from request.json
    # Call ROS2 service /zone/save
    # Return JSON response
    pass
```

### Step 4.3: Test Web UI

```bash
# Start web server
./start-web-server.sh

# Open browser: http://<robot-ip>:8080/zone_manager
# Draw a polygon on the map
# Click "Save Zone"
# Verify YAML file created in /zones/
```

✅ **Checkpoint**: Can draw zones via web interface!

---

## 📊 Phase A Complete - Verification

Run these checks to verify Phase A is complete:

```bash
# 1. Check messages built
ros2 interface list | grep rosmower_msgs

# 2. Battery monitor running
ros2 node list | grep battery_monitor

# 3. Zone manager running
ros2 node list | grep zone_manager

# 4. Topics active
ros2 topic list | grep -E "battery|zone"

# 5. Services available
ros2 service list | grep zone

# 6. Zones directory has files
ls -lh /ws/zones/
```

**Success Criteria:**
- ✅ rosmower_msgs package builds without errors
- ✅ battery_monitor responds to /percent changes
- ✅ zone_manager loads zones from YAML
- ✅ Web UI displays and can draw polygons
- ✅ At least 1 zone saved and loaded successfully

---

## 🎯 Next Steps

Once Phase A is complete, proceed to:
- **Phase B**: Path planning and mission manager
- See `IMPLEMENTATION_CHECKLIST.md` for detailed steps

---

## 🐛 Troubleshooting

### Messages not found
```bash
# Rebuild and source
cd /mnt/nova_ssd/rosmowercompleate
colcon build --packages-select rosmower_msgs
source install/setup.bash
```

### Battery monitor not receiving data
```bash
# Check battery topics exist
ros2 topic list | grep -E "percent|current"

# Echo to see data
ros2 topic echo /percent
```

### Zone manager can't find zones
```bash
# Check directory exists and has correct path
ls -la /ws/zones/
# Or wherever zones are mounted in Docker
```

### Web UI can't connect to ROS2
- Ensure web_server.py has ROS2 bridge code
- Check CycloneDDS allows external connections
- Verify Docker network settings

---

## 📚 Additional Resources

- Full analysis: `ARCHITECTURE_ANALYSIS.md`
- Complete checklist: `IMPLEMENTATION_CHECKLIST.md`
- Visual summary: `ARCHITECTURE_SUMMARY.txt`

**Estimated Time for Phase A**: 12-16 hours over 1-2 weeks

Good luck! 🚀
