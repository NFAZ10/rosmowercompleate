# Multi-Zone Route Management - Quick Start Guide

## 🚀 5-Minute Quick Start

### Prerequisites Check
```bash
# Verify ROS2 workspace
ls /ws/src/rosmower_msgs
ls /ws/src/rosmower

# Check if built
ls /ws/install/rosmower_msgs
ls /ws/install/rosmower

# Check storage directories
mkdir -p /ws/zones /ws/routes
```

### Build and Launch
```bash
# Build packages (if needed)
cd /ws
colcon build --packages-select rosmower_msgs rosmower
source install/setup.bash

# Launch multi-zone system
ros2 launch rosmower zone_and_route_management.launch.py
```

### Start Web Interface
```bash
# In new terminal
cd /mnt/nova_ssd/rosmowercompleate
./start-web-server.sh
# OR
python3 web_server.py
```

### Access Web UI
Open browser: `http://<robot-ip>:5000/routes`

---

## 📝 Record Your First Route

### Step 1: Define Zones (if not done)
1. Go to: `http://<robot-ip>:5000/zones/recorder`
2. Walk perimeter of each zone
3. Save zones

### Step 2: Record Transit Route
1. Go to: `http://<robot-ip>:5000/routes`
2. Select FROM zone (e.g., "backyard")
3. Select TO zone (e.g., "frontyard")
4. Choose route type: "DRIVEWAY"
5. Set speed: 0.5 m/s
6. Set width: 2.0 meters
7. Check "Bidirectional"
8. Click "Start Recording"
9. Walk the route slowly (0.5 m/s)
10. Click "Stop Recording"
11. Verify route appears in list

### Step 3: View Zone Graph
1. On routes page, see graph visualization
2. Verify zones connected by route
3. Test path planning (future feature)

---

## 🔍 Verify Installation

### Check ROS2 Topics
```bash
# Should see these topics
ros2 topic list

# Expected:
# /zones
# /zones/graph
# /routes/all
# /route/recording/status
# /route/recording/path
# /gps/fix
```

### Check ROS2 Services
```bash
# Should see these services
ros2 service list | grep -E "(zone|route)"

# Expected:
# /zone/save, /zone/load, /zone/list, /zone/delete
# /route/record/start, /route/record/stop
# /route/record/control
# /route/list, /route/delete
# /route/plan_path
```

### Check Nodes Running
```bash
ros2 node list

# Expected:
# /zone_manager
# /route_manager
# /route_planner
```

---

## 📊 Test Commands

### List All Zones
```bash
ros2 service call /zone/list rosmower_msgs/srv/ListZones "{}"
```

### List All Routes
```bash
ros2 service call /route/list rosmower_msgs/srv/ListRoutes \
  "{from_zone_id: '', to_zone_id: '', route_type: ''}"
```

### View Zone Graph
```bash
ros2 topic echo /zones/graph --once
```

### Monitor Route Recording
```bash
ros2 topic echo /route/recording/status
```

---

## 🎯 Common Parameters

### Route Manager Parameters
```yaml
routes_directory: "/ws/routes"
min_gps_quality_hdop: 2.0      # Lower = stricter (1.0 very strict, 3.0 lenient)
waypoint_spacing_meters: 1.0    # Minimum spacing between waypoints
max_recording_time_seconds: 600 # Auto-pause after 10 minutes
```

### Adjust GPS Quality Threshold
```bash
# More lenient (accept more waypoints)
ros2 param set /route_manager min_gps_quality_hdop 3.0

# Stricter (reject poor GPS)
ros2 param set /route_manager min_gps_quality_hdop 1.5
```

---

## 📂 File Locations

### Zones
```
/ws/zones/
├── backyard.yaml
├── frontyard.yaml
└── sideyard.yaml
```

### Routes
```
/ws/routes/
├── backyard_to_frontyard_20240115_103000.yaml
├── frontyard_to_sideyard_20240115_104500.yaml
└── zone_graph.yaml (auto-generated)
```

### Web Interface
```
/mnt/nova_ssd/rosmowercompleate/src/rosmower/web/
├── zone_routes.html      # Main route management UI
├── zone_recorder.html    # Zone recording UI
├── zone_manager.html     # Zone management UI
└── mode_control.html     # System control UI
```

### Documentation
```
/mnt/nova_ssd/rosmowercompleate/
├── MULTI_ZONE_GUIDE.md           # Complete system guide
├── ROUTE_RECORDING_GUIDE.md      # Step-by-step recording
├── ROUTE_BEST_PRACTICES.md       # Advanced tips
├── ZONE_GRAPH_EXPLAINED.md       # Graph theory concepts
└── MULTI_ZONE_IMPLEMENTATION_COMPLETE.md  # Implementation summary
```

---

## 🐛 Quick Troubleshooting

### GPS Quality Poor
```bash
# Check GPS status
ros2 topic echo /gps/fix --once

# View GPS quality in web UI
# Green = good, Yellow = acceptable, Red = poor

# If persistent red:
# - Move to open area
# - Wait for satellite lock
# - Check GPS antenna
# - Increase HDOP threshold temporarily
```

### Route Not Saving
```bash
# Check route manager logs
ros2 node info /route_manager

# Common issues:
# - Less than 2 waypoints (walk longer)
# - Route too short (< 2 meters)
# - GPS quality too poor
# - Zone IDs don't match existing zones
```

### Nodes Not Starting
```bash
# Check if already running
ros2 node list

# Restart launch
ros2 launch rosmower zone_and_route_management.launch.py
```

### Web Server Not Accessible
```bash
# Check if running
ps aux | grep web_server

# Check port
netstat -tuln | grep 5000

# Restart
./start-web-server.sh
```

---

## 📖 Next Steps

1. **Read Documentation**: Start with `MULTI_ZONE_GUIDE.md`
2. **Record Zones**: Use zone recorder if not done
3. **Record Routes**: Connect all your zones
4. **Verify Graph**: Check zone connectivity
5. **Set Priorities**: Order zones for mowing
6. **Test System**: Use test script
7. **Field Test**: Record real routes in your yard

---

## 🧪 Run Tests

```bash
# Comprehensive test suite
./test_multi_zone_routes.sh --verbose

# Expected output:
# ✓ Route file validation
# ✓ GPS quality filtering
# ✓ Bidirectional routes
# ✓ Zone graph generation
# ✓ Dijkstra path planning
# ✓ Disconnected zone detection
# ✓ Web API endpoints
```

---

## 🎓 Learning Path

1. **Beginner**: `MULTI_ZONE_GUIDE.md` - System overview
2. **User**: `ROUTE_RECORDING_GUIDE.md` - How to record routes
3. **Advanced**: `ROUTE_BEST_PRACTICES.md` - Optimization tips
4. **Expert**: `ZONE_GRAPH_EXPLAINED.md` - Graph theory deep dive

---

## 💡 Pro Tips

1. **GPS Quality**: Record on clear days, open areas
2. **Walking Speed**: Slow and steady (0.3-0.5 m/s)
3. **Bidirectional**: Most routes should be bidirectional
4. **Route Types**: Choose appropriate type for safety
5. **Speed Limits**: Start conservative, increase later
6. **Path Width**: Account for GPS drift (2-3m typical)
7. **Validation**: Always verify routes in zone graph
8. **Documentation**: Note route changes in comments

---

## ✅ System Status Check

```bash
#!/bin/bash
echo "=== Multi-Zone System Status ==="

echo -n "Zone Manager: "
ros2 node list | grep -q zone_manager && echo "✓ Running" || echo "✗ Not running"

echo -n "Route Manager: "
ros2 node list | grep -q route_manager && echo "✓ Running" || echo "✗ Not running"

echo -n "Route Planner: "
ros2 node list | grep -q route_planner && echo "✓ Running" || echo "✗ Not running"

echo -n "Web Server: "
curl -s http://localhost:5000 > /dev/null && echo "✓ Running" || echo "✗ Not running"

echo -n "GPS: "
ros2 topic list | grep -q gps/fix && echo "✓ Available" || echo "✗ Not available"

echo ""
echo "Zones: $(ls /ws/zones/*.yaml 2>/dev/null | wc -l)"
echo "Routes: $(ls /ws/routes/*.yaml 2>/dev/null | wc -l)"
echo ""
```

Save and run: `./check_system_status.sh`

---

## 📞 Support

**Documentation**:
- Complete Guide: `MULTI_ZONE_GUIDE.md`
- Recording Guide: `ROUTE_RECORDING_GUIDE.md`
- Best Practices: `ROUTE_BEST_PRACTICES.md`
- Graph Concepts: `ZONE_GRAPH_EXPLAINED.md`

**Logs**:
```bash
# View node logs
ros2 node info /route_manager
ros2 node info /zone_manager
ros2 node info /route_planner

# Monitor topics
ros2 topic echo /route/recording/status
ros2 topic echo /zones/graph
```

**Common Issues**: See `MULTI_ZONE_GUIDE.md` troubleshooting section

---

**Happy Multi-Zone Mowing!** 🎉🤖🌱
