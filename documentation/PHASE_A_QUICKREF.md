# Phase A Quick Reference

## 🚀 Quick Start Commands

### Build Packages
```bash
./build-phase-a.sh
```

### Launch Autonomous Mission Nodes
```bash
# Inside Docker container
./docker-helper.sh exec ros2 launch rosmower autonomous_mission.launch.py

# Or run nodes individually
./docker-helper.sh exec ros2 run rosmower battery_monitor.py
./docker-helper.sh exec ros2 run rosmower zone_manager.py
```

### Access Web Interface
- **Zone Manager**: http://localhost:8080/zones
- **Mode Control**: http://localhost:8080/mode_control.html
- **Main Dashboard**: http://localhost:8080/

## 📡 ROS2 Topics

### Published Topics
| Topic | Type | Description |
|-------|------|-------------|
| `/battery/state` | std_msgs/String | Battery state (NORMAL, LOW, CRITICAL, CHARGING, CHARGED) |
| `/battery/low` | std_msgs/Bool | Low battery flag |
| `/mission/command` | std_msgs/String | Mission commands (RETURN_TO_DOCK, EMERGENCY_DOCK, etc.) |
| `/zones` | rosmower_msgs/ZoneArray | All available zones |
| `/zone/current` | rosmower_msgs/Zone | Currently active zone |

### Subscribed Topics
| Topic | Type | Description |
|-------|------|-------------|
| `/percent` | std_msgs/Float32 | Battery percentage (0-100) |
| `/current` | std_msgs/Float32 | Battery current in Amps (negative = charging) |

## 🔧 ROS2 Services

### Zone Management Services
```bash
# List all zones
ros2 service call /zone/list rosmower_msgs/srv/ListZones

# Save a zone (typically done via web UI)
ros2 service call /zone/save rosmower_msgs/srv/SaveZone "{zone: {...}}"

# Load a specific zone
ros2 service call /zone/load rosmower_msgs/srv/LoadZone "{zone_id: 'front_yard'}"

# Delete a zone
ros2 service call /zone/delete rosmower_msgs/srv/DeleteZone "{zone_id: 'test_zone'}"
```

## 🧪 Testing Commands

### Test Battery Monitor

#### Terminal 1: Start battery monitor
```bash
./docker-helper.sh exec ros2 run rosmower battery_monitor.py
```

#### Terminal 2: Monitor battery state
```bash
./docker-helper.sh exec ros2 topic echo /battery/state
```

#### Terminal 3: Simulate battery changes
```bash
# Normal state (100%)
./docker-helper.sh exec ros2 topic pub /percent std_msgs/msg/Float32 "data: 100.0"

# Low battery (triggers RETURN_TO_DOCK)
./docker-helper.sh exec ros2 topic pub /percent std_msgs/msg/Float32 "data: 20.0"

# Critical battery (triggers EMERGENCY_DOCK)
./docker-helper.sh exec ros2 topic pub /percent std_msgs/msg/Float32 "data: 10.0"

# Charging state
./docker-helper.sh exec ros2 topic pub /percent std_msgs/msg/Float32 "data: 50.0"
./docker-helper.sh exec ros2 topic pub /current std_msgs/msg/Float32 "data: -5.0"

# Fully charged
./docker-helper.sh exec ros2 topic pub /percent std_msgs/msg/Float32 "data: 96.0"
./docker-helper.sh exec ros2 topic pub /current std_msgs/msg/Float32 "data: -0.5"
```

### Test Zone Manager

#### Start zone manager
```bash
./docker-helper.sh exec ros2 run rosmower zone_manager.py
```

#### List zones
```bash
./docker-helper.sh exec ros2 service call /zone/list rosmower_msgs/srv/ListZones
```

#### View zones topic
```bash
./docker-helper.sh exec ros2 topic echo /zones --once
```

#### View current zone
```bash
./docker-helper.sh exec ros2 topic echo /zone/current --once
```

### Test Web Interface

1. Start web server: `./start-web-server.sh`
2. Open browser: http://localhost:8080/zones
3. **Draw a zone**:
   - Click on canvas to add vertices
   - Minimum 3 points required
   - Double-click to close polygon
4. **Configure zone**:
   - Enter Zone ID (e.g., "backyard")
   - Enter Zone Name (e.g., "Back Yard")
   - Set Priority (1-10, higher = earlier)
   - Check "Enabled" checkbox
5. **Save zone**: Click "Save Zone" button
6. **Verify**: Check that file appears in `zones/` directory

## 📁 File Locations

### Custom Messages
```
src/rosmower_msgs/msg/
├── Zone.msg           # Zone definition with GPS coordinates
├── ZoneArray.msg      # Array of zones
├── BatteryStatus.msg  # Enhanced battery status
└── Mission.msg        # Mission definition
```

### Services
```
src/rosmower_msgs/srv/
├── SaveZone.srv       # Save zone to disk
├── LoadZone.srv       # Load zone from disk
├── ListZones.srv      # List all zones
└── DeleteZone.srv     # Delete a zone
```

### Nodes
```
src/rosmower/scripts/
├── battery_monitor.py  # Battery state monitoring and triggers
└── zone_manager.py     # Zone storage and management
```

### Configuration
```
src/rosmower/config/
└── autonomous_mission.yaml  # Node parameters
```

### Launch Files
```
src/rosmower/launch/
└── autonomous_mission.launch.py  # Launch both nodes
```

### Persistent Storage
```
zones/
├── front_yard.yaml     # Sample front yard zone
├── back_yard.yaml      # Sample back yard zone
└── [custom zones]      # Your custom zones
```

### Web Interface
```
src/rosmower/web/
├── zone_manager.html   # Zone drawing and management UI
└── mode_control.html   # Updated with zone link
```

## ⚙️ Configuration Parameters

### Battery Monitor Parameters
Edit `src/rosmower/config/autonomous_mission.yaml`:

```yaml
battery_monitor:
  ros__parameters:
    low_battery_threshold: 25.0        # % - Start return to dock
    critical_battery_threshold: 15.0    # % - Emergency dock NOW
    charged_threshold: 95.0             # % - Consider fully charged
    charging_current_threshold: -0.1    # A - Negative = charging
```

### Zone Manager Parameters
```yaml
zone_manager:
  ros__parameters:
    zones_directory: /ws/zones    # Where zone files are stored
    publish_rate: 1.0              # Hz - How often to publish zones
    frame_id: map                  # TF frame for coordinates
```

## 🔍 Debugging Commands

### Check if messages are built
```bash
./docker-helper.sh exec ros2 interface list | grep rosmower_msgs
```

### View message definition
```bash
./docker-helper.sh exec ros2 interface show rosmower_msgs/msg/Zone
./docker-helper.sh exec ros2 interface show rosmower_msgs/msg/BatteryStatus
```

### Check running nodes
```bash
./docker-helper.sh exec ros2 node list
```

### View node info
```bash
./docker-helper.sh exec ros2 node info /battery_monitor
./docker-helper.sh exec ros2 node info /zone_manager
```

### Check topic data rate
```bash
./docker-helper.sh exec ros2 topic hz /battery/state
./docker-helper.sh exec ros2 topic hz /zones
```

### View raw topic data
```bash
./docker-helper.sh exec ros2 topic echo /battery/state
./docker-helper.sh exec ros2 topic echo /zones
```

### Monitor logs
```bash
./docker-helper.sh exec ros2 run rqt_console rqt_console
```

## 🌐 Web API Endpoints

### Zone Management
```bash
# List all zones (JSON)
curl http://localhost:8080/api/zones

# Save a zone (JSON)
curl -X POST http://localhost:8080/api/zones/save \
  -H "Content-Type: application/json" \
  -d '{"id":"test","name":"Test Zone","vertices":[...]}'

# Delete a zone
curl -X DELETE http://localhost:8080/api/zones/delete/test_zone

# Get battery status
curl http://localhost:8080/api/battery/status
```

## 📊 Battery State Transitions

```
              ┌─────────────┐
              │   NORMAL    │ (>25%)
              └─────┬───────┘
                    │ Battery drops below 25%
                    ↓ (Triggers: RETURN_TO_DOCK)
              ┌─────────────┐
              │     LOW     │ (15-25%)
              └─────┬───────┘
                    │ Battery drops below 15%
                    ↓ (Triggers: EMERGENCY_DOCK)
              ┌─────────────┐
              │  CRITICAL   │ (<15%)
              └─────┬───────┘
                    │ Robot reaches dock
                    ↓ (Current < -0.1A)
              ┌─────────────┐
              │  CHARGING   │
              └─────┬───────┘
                    │ Battery reaches 95%
                    ↓
              ┌─────────────┐
              │   CHARGED   │ (Triggers: BATTERY_CHARGED)
              └─────────────┘
```

## 🐛 Common Issues

### Messages not found
```bash
# Rebuild packages
./build-phase-a.sh

# Verify messages are available
./docker-helper.sh exec ros2 interface list | grep rosmower_msgs
```

### Nodes can't find zones directory
```bash
# Check directory exists and is mounted
ls -la zones/

# Create if missing
mkdir -p zones

# Restart Docker with proper volume mounts
./docker-helper.sh run
```

### Web UI not loading
```bash
# Check web server is running
ps aux | grep web_server

# Start web server
./start-web-server.sh

# Check logs
tail -f logs/web_server.log
```

### Battery monitor not receiving data
```bash
# Check if topics exist
./docker-helper.sh exec ros2 topic list | grep -E "percent|current"

# Manually publish test data
./docker-helper.sh exec ros2 topic pub /percent std_msgs/msg/Float32 "data: 50.0"

# Monitor what battery_monitor receives
./docker-helper.sh exec ros2 topic echo /percent
```

## 📚 Documentation

- **Full Guide**: `PHASE_A_COMPLETE.md`
- **Summary**: `PHASE_A_SUMMARY.txt`
- **Implementation Plan**: `QUICKSTART_PHASE_A.md`
- **Next Phase**: `QUICKSTART_PHASE_B.md`

## ✅ Quick Verification

Run the automated verification:
```bash
./verify-phase-a.sh
```

Run the interactive test script:
```bash
./test-phase-a.sh
```

---

**Phase A Status**: ✅ COMPLETE  
**Next Phase**: B - Path Planning and Mission Execution
