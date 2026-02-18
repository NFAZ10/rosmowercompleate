# 🚀 Multi-Zone Route Management - Quick Reference Card

## System Status

```bash
# Check if running
ros2 node list | grep -E "zone_manager|route_manager|route_planner"

# Start all components
ros2 launch rosmower zone_and_route_management.launch.py

# Web interface
http://<robot-ip>:8080/routes
```

## Route Recording - Quick Steps

1. **Pre-Check**
   - ✅ GPS Quality = Green (HDOP < 2.0)
   - ✅ Both zones defined
   - ✅ Clear weather

2. **Record**
   - Select from/to zones
   - Set route type & parameters
   - Click "Start Recording"
   - Walk slowly (0.5 m/s)
   - Click "Stop & Save"

3. **Verify**
   - Route appears in list
   - Graph shows connection
   - Waypoints > 2

## Key Parameters

| Parameter | Default | Recommended |
|-----------|---------|-------------|
| GPS Quality (HDOP) | < 2.0 | < 1.5 for critical routes |
| Walking Speed | 0.5 m/s | 0.3-0.7 m/s |
| Waypoint Spacing | 1.0 m | 0.5-2.0 m depending on route |
| Path Width Buffer | +2m | Physical width + 2-3m |

## Route Types

| Type | Use Case | Speed | Width |
|------|----------|-------|-------|
| DRIVEWAY | Wide, paved | 0.5-0.6 m/s | 4-6m |
| GATE_PASSAGE | Narrow gates | 0.2-0.3 m/s | 2-3m |
| AROUND_BUILDING | Around structures | 0.3-0.5 m/s | 3-5m |
| NARROW_PATH | Tight spaces | 0.2-0.4 m/s | 2-4m |
| ROAD_CROSSING | Cross roads | 0.3-0.4 m/s | 3-5m |

## Common Commands

```bash
# List all routes
ros2 topic echo /routes/all --once

# View zone graph
ros2 topic echo /zones/graph --once

# Recording status
ros2 topic echo /route/recording/status

# Plan path (with future custom service)
ros2 service call /route/plan_path rosmower_msgs/srv/PlanPath \
  "{start_zone: 'backyard', end_zone: 'frontyard'}"

# Manual service calls (current)
ros2 service call /route/record/start std_srvs/srv/Trigger
ros2 service call /route/record/stop std_srvs/srv/Trigger
```

## File Locations

```
/ws/zones/           - Zone definitions (YAML)
/ws/routes/          - Route definitions (YAML)
/ws/routes/README.md - Route format guide

src/rosmower/scripts/
  ├── zone_manager.py     - Zone & graph management
  ├── route_manager.py    - Route recording
  └── route_planner.py    - Path planning

src/rosmower/web/
  └── zone_routes.html    - Web UI
```

## Troubleshooting Quick Fixes

| Problem | Quick Fix |
|---------|-----------|
| GPS quality poor | Wait 5 min, move to open area |
| No waypoints | Check HDOP < 2.0, walk slower |
| Route not in graph | Verify zone IDs match zone files |
| Web UI not loading | Restart: `./start-web-server.sh` |
| Nodes not starting | Rebuild: `colcon build --packages-select rosmower` |

## GPS Quality Guide

```
HDOP < 1.0   🟢 Excellent - Record anytime
HDOP 1.0-2.0 🟢 Good      - Record routes
HDOP 2.0-5.0 🟡 Fair      - Wait for better
HDOP > 5.0   🔴 Poor      - Do not record
```

## Safety Checklist

Before autonomous use:
- [ ] Route recorded with HDOP < 2.0
- [ ] Path width includes 2m GPS buffer
- [ ] Speed limit is conservative
- [ ] All waypoints in safe areas
- [ ] Route visually validated
- [ ] Emergency stop accessible

## Documentation

| Doc | Purpose |
|-----|---------|
| IMPLEMENTATION_SUMMARY.md | Build & deploy guide |
| MULTI_ZONE_GUIDE.md | System overview |
| ROUTE_RECORDING_GUIDE.md | Step-by-step recording |
| ROUTE_BEST_PRACTICES.md | Expert tips |
| ZONE_GRAPH_EXPLAINED.md | Theory & algorithms |

## Test & Build

```bash
# Run tests
./test_multi_zone_routes.sh

# Setup storage
./setup_multi_zone_storage.sh

# Build messages
cd /ws && colcon build --packages-select rosmower_msgs

# Build nodes
cd /ws && colcon build --packages-select rosmower

# Source workspace
source /ws/install/setup.bash
```

## Web API Endpoints

```
GET  /api/routes/list                - List all routes
POST /api/routes/record/start        - Start recording
POST /api/routes/record/stop         - Stop & save
POST /api/routes/record/pause        - Pause recording
POST /api/routes/record/resume       - Resume recording
POST /api/routes/record/cancel       - Cancel without save
DELETE /api/routes/delete/<route_id> - Delete route
GET  /api/routes/status              - Recording status
GET  /api/zones/graph                - Zone connectivity
POST /api/zones/update_priority      - Update zone priority
```

## ROS2 Topics

```
/zones                      - ZoneArray
/zones/graph                - ZoneGraph
/routes/all                 - RouteArray
/route/recording/status     - RouteRecordingStatus
/route/recording/path       - Path (visualization)
/route/active               - Route (selected)
/gps/fix                    - NavSatFix (input)
```

## Performance Expectations

| Property | Zones | Routes | Load Time | Path Plan |
|----------|-------|--------|-----------|-----------|
| Small | 3-5 | 5-10 | < 1s | < 1ms |
| Medium | 10-20 | 30-50 | < 2s | < 5ms |
| Large | 50+ | 150+ | < 5s | < 20ms |

---

**🎯 Quick Start:** 
1. `./start-web-server.sh`
2. `ros2 launch rosmower zone_and_route_management.launch.py`
3. Open `http://<robot-ip>:8080/routes`
4. Record your first route!

**📚 Full docs:** See IMPLEMENTATION_SUMMARY.md

**✨ Pro tip:** Always wait for GPS quality = Green before recording!
