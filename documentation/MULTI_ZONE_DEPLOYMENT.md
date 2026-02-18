# Multi-Zone Route Management - Deployment Guide

## 🚀 Deployment Checklist

This guide walks you through deploying the complete multi-zone route management system to your autonomous mower.

---

## Prerequisites

✅ **Hardware Requirements:**
- GPS receiver (u-blox F9P or compatible) connected and publishing `/gps/fix`
- Jetson Nano or similar compute platform
- Network connectivity (WiFi or Ethernet)

✅ **Software Requirements:**
- ROS2 Humble installed
- Docker (optional, for containerized deployment)
- Python 3.8+
- Web browser for UI access

✅ **Existing System:**
- Zone recording system operational (Phase A complete)
- At least 2 zones defined in `/ws/zones/`
- GPS receiving valid fixes

---

## Step 1: Build the System

### Option A: Native Build (Recommended for Development)

```bash
cd /mnt/nova_ssd/rosmowercompleate

# Build message types first
colcon build --packages-select rosmower_msgs
source install/setup.bash

# Build main package
colcon build --packages-select rosmower
source install/setup.bash

# Verify build
ls install/rosmower_msgs/share/rosmower_msgs/msg/
# Should show: Route.msg, RouteArray.msg, ZoneGraph.msg, etc.
```

**Expected Output:**
```
Starting >>> rosmower_msgs
Finished <<< rosmower_msgs [10.5s]
Starting >>> rosmower
Finished <<< rosmower [5.2s]

Summary: 2 packages finished [15.7s]
```

### Option B: Docker Build

```bash
cd /mnt/nova_ssd/rosmowercompleate

# Build Docker image
./build-docker.sh

# Or manually
docker build -t rosmower:latest .
```

---

## Step 2: Initialize Storage

```bash
# Create routes directory and examples
./setup_multi_zone_storage.sh
```

**This creates:**
```
/ws/routes/                    # Route storage directory
/ws/routes/examples/           # Example routes
/ws/routes/examples/example_driveway.yaml
```

**Verify:**
```bash
ls -la /ws/routes/
# Should show routes/ directory with proper permissions
```

---

## Step 3: Verify GPS

Before launching, ensure GPS is working:

```bash
# Check GPS topic
ros2 topic list | grep gps
# Should show: /gps/fix

# Monitor GPS data
ros2 topic echo /gps/fix --once

# Check GPS quality (HDOP should be < 2.0 for good signal)
ros2 topic echo /gps/fix | grep position_covariance
```

**GPS Quality Reference:**
- HDOP < 2.0: 🟢 Excellent (safe to record routes)
- HDOP 2-5: 🟡 Fair (wait for better signal)
- HDOP > 5: 🔴 Poor (do not record)

**If GPS is not working:**
```bash
# Check GPS hardware
./find_gps.sh

# Configure GPS
./configure_gps.py

# Test GPS standalone
./test_gps_standalone.py
```

---

## Step 4: Launch the System

### Option A: Launch with ROS2

**Terminal 1: Launch Route Management Nodes**
```bash
cd /mnt/nova_ssd/rosmowercompleate
source install/setup.bash

ros2 launch rosmower zone_and_route_management.launch.py
```

**Expected Output:**
```
[INFO] [launch]: Launching zone and route management system...
[INFO] [zone_manager]: Zone manager started
[INFO] [route_manager]: Route manager started, monitoring GPS
[INFO] [route_planner]: Route planner ready
```

**Terminal 2: Launch Web Server**
```bash
cd /mnt/nova_ssd/rosmowercompleate
./start-web-server.sh

# Or manually
python3 web_server.py
```

**Expected Output:**
```
 * Serving Flask app 'web_server'
 * Running on http://0.0.0.0:8080
 * Route management endpoints loaded
```

### Option B: Launch with Docker

```bash
cd /mnt/nova_ssd/rosmowercompleate

# Start all services
docker-compose up -d

# View logs
docker-compose logs -f
```

---

## Step 5: Access Web Interface

Open your browser and navigate to:

```
http://<robot-ip>:8080/routes
```

**Replace `<robot-ip>` with:**
- `localhost` if on the robot
- Robot's IP address (e.g., `192.168.1.100`) if remote

**You should see:**
- Zone list on the left
- Route recording controls in the center
- Zone connectivity graph on the right
- GPS quality indicator at the top

---

## Step 6: Verify System Health

### Check ROS2 Nodes

```bash
ros2 node list
```

**Expected Output:**
```
/route_manager
/route_planner
/zone_manager
```

### Check ROS2 Topics

```bash
ros2 topic list | grep -E "(route|zone)"
```

**Expected Output:**
```
/route/recording/status
/route/recording/path
/routes/all
/route/active
/zones/graph
/zones/all
```

### Check ROS2 Services

```bash
ros2 service list | grep route
```

**Expected Output:**
```
/route/record/start
/route/record/stop
/route/record/pause
/route/record/resume
/route/record/cancel
/route/plan_path
```

### Monitor Route Recording Status

```bash
ros2 topic echo /route/recording/status
```

**Expected Output (when idle):**
```
is_recording: false
is_paused: false
current_route_id: ''
waypoints_collected: 0
current_gps_lat: 37.12345
current_gps_lon: -122.12345
current_gps_quality: 1.2
```

---

## Step 7: Record Your First Route

### 7.1 Check GPS Quality

In the web UI, look for the GPS quality indicator:
- 🟢 **GREEN** = Ready to record
- 🟡 **YELLOW** = Wait for better signal
- 🔴 **RED** = GPS too poor, cannot record

**If RED or YELLOW:**
- Move to an open area
- Wait 2-5 minutes for GPS to stabilize
- Check `/gps/fix` topic for valid data

### 7.2 Configure Route

In the web UI:

1. **From Zone:** Select starting zone (e.g., "backyard")
2. **To Zone:** Select destination zone (e.g., "frontyard")
3. **Route Name:** Enter descriptive name (e.g., "Main Driveway")
4. **Route Type:** Select appropriate type
   - DRIVEWAY: Wide paved paths (2-5m)
   - GATE_PASSAGE: Gates and narrow passages (1-2m)
   - AROUND_BUILDING: Routes around structures
   - NARROW_PATH: Tight spaces
   - ROAD_CROSSING: Crosses roads (use caution)
5. **Max Speed:** Set safe speed (e.g., 0.5 m/s)
6. **Path Width:** Set path width (e.g., 2.5 m)
7. **Bidirectional:** ✓ Check if route works both ways
8. **Mow During Transit:** ☐ Usually leave unchecked

### 7.3 Start Recording

1. Click **"Start Recording"** button
2. Status changes to "Recording..."
3. Waypoint counter starts incrementing
4. Distance counter shows cumulative distance

### 7.4 Walk the Route

- Walk slowly along the desired path (normal walking pace)
- Stay on the path you want the robot to follow
- The system collects GPS waypoints every ~1 meter
- Watch the waypoint counter increase

**Tips:**
- Walk at steady pace (don't run)
- Follow the centerline of the path
- Avoid sharp turns if possible
- Keep clear line of sight to sky for GPS

### 7.5 Stop and Save

1. When you reach the destination zone, click **"Stop & Save Route"**
2. System validates the route (minimum 2 waypoints required)
3. Route is saved to `/ws/routes/`
4. Route appears in the route list
5. Zone graph automatically updates

**Verification:**
```bash
# Check saved route
ls -lt /ws/routes/ | head -5

# View route details
cat /ws/routes/backyard_to_frontyard_*.yaml
```

---

## Step 8: Test Route Planning

### Via Web UI (Future Feature)
Select zones and click "Plan Path" to find shortest route.

### Via Command Line

```bash
# Plan path from backyard to frontyard
ros2 service call /route/plan_path rosmower_msgs/srv/PlanPath \
  "{start_zone: 'backyard', end_zone: 'frontyard'}"
```

**Expected Response:**
```yaml
success: true
route_ids: ['route_001_backyard_to_frontyard']
total_distance: 15.3
estimated_time: 30.6
message: 'Path found successfully'
```

---

## Step 9: View Zone Graph

### Via Web UI
The zone connectivity graph is displayed on the right panel showing:
- Circles = Zones
- Lines = Routes
- Colors = Route types

### Via ROS2 Topic

```bash
ros2 topic echo /zones/graph
```

**Expected Output:**
```yaml
nodes:
  - zone_id: 'backyard'
    zone_name: 'Back Yard'
    center_lat: 37.12345
    center_lon: -122.12345
    priority: 5
edges:
  - from_zone_id: 'backyard'
    to_zone_id: 'frontyard'
    route_id: 'route_001'
    distance_meters: 15.3
    bidirectional: true
```

---

## Step 10: Production Deployment

### Auto-Start on Boot

Create systemd service:

```bash
sudo nano /etc/systemd/system/rosmower-routes.service
```

```ini
[Unit]
Description=ROS Mower Route Management
After=network.target

[Service]
Type=simple
User=rosmower
WorkingDirectory=/mnt/nova_ssd/rosmowercompleate
ExecStart=/bin/bash -c "source /opt/ros/humble/setup.bash && source install/setup.bash && ros2 launch rosmower zone_and_route_management.launch.py"
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable rosmower-routes.service
sudo systemctl start rosmower-routes.service
```

### Web Server Auto-Start

The web server can be started with the existing `rosmower-web.service`:

```bash
sudo systemctl enable rosmower-web.service
sudo systemctl start rosmower-web.service
```

---

## Troubleshooting

### GPS Not Publishing

**Symptom:** No `/gps/fix` topic

**Solution:**
```bash
# Find GPS device
./find_gps.sh

# Check USB devices
ls /dev/ttyACM* /dev/ttyUSB*

# Test GPS connection
./test_gps_standalone.py
```

### Poor GPS Quality

**Symptom:** GPS quality indicator always RED

**Solution:**
- Move to open area with clear sky view
- Wait 5-10 minutes for GPS to acquire satellites
- Check antenna connection
- Avoid recording during heavy cloud cover or near buildings

### Route Not Saving

**Symptom:** Route disappears after recording

**Solution:**
```bash
# Check directory permissions
ls -ld /ws/routes/
sudo chown -R $USER:$USER /ws/routes/

# Check disk space
df -h /ws/

# View route manager logs
ros2 node logs route_manager
```

### Web UI Not Loading

**Symptom:** Browser cannot connect to http://robot-ip:8080/routes

**Solution:**
```bash
# Check web server is running
ps aux | grep web_server

# Restart web server
./start-web-server.sh

# Check firewall
sudo ufw allow 8080/tcp

# Test locally
curl http://localhost:8080/api/routes/list
```

### Nodes Not Starting

**Symptom:** `ros2 node list` doesn't show route nodes

**Solution:**
```bash
# Check for build errors
colcon build --packages-select rosmower --event-handlers console_direct+

# Source workspace
source install/setup.bash

# Launch with verbose logging
ros2 launch rosmower zone_and_route_management.launch.py --screen

# Check ROS_DOMAIN_ID
echo $ROS_DOMAIN_ID
```

### Zone Graph Empty

**Symptom:** Zone graph shows no connections

**Solution:**
- Record at least one route between zones
- Check that zones exist in `/ws/zones/`
- Restart zone_manager to regenerate graph:
  ```bash
  ros2 lifecycle set /zone_manager shutdown
  ros2 run rosmower zone_manager
  ```

---

## Performance Tuning

### Reduce GPS Waypoint Frequency

If routes have too many waypoints:

```bash
ros2 param set /route_manager waypoint_spacing_meters 2.0
```

### Adjust GPS Quality Threshold

If GPS quality is always marginal:

```bash
# More permissive (allows HDOP up to 3.0)
ros2 param set /route_manager min_gps_quality_hdop 3.0

# More strict (requires HDOP < 1.5)
ros2 param set /route_manager min_gps_quality_hdop 1.5
```

### Increase Recording Time Limit

For longer routes:

```bash
ros2 param set /route_manager max_recording_time_seconds 1200  # 20 minutes
```

---

## Monitoring and Maintenance

### Daily Checks

```bash
# Check system health
./test_multi_zone_routes.sh

# View recent routes
ls -lt /ws/routes/ | head -10

# Check GPS quality
ros2 topic echo /route/recording/status --once
```

### Weekly Maintenance

- Review and delete unused routes
- Validate route quality by re-walking
- Update zone priorities based on mowing schedule
- Check for GPS drift and re-record critical routes

### Monthly Maintenance

- Backup routes directory: `tar -czf routes_backup.tar.gz /ws/routes/`
- Review zone graph connectivity
- Update documentation with new routes
- Test path planning between all zones

---

## Integration with Mission Planner

Once routes are recorded, integrate with your mission planner:

```python
# Example mission planner integration
from rosmower_msgs.srv import PlanPath

# Create service client
plan_path_client = self.create_client(PlanPath, '/route/plan_path')

# Request path
request = PlanPath.Request()
request.start_zone = 'backyard'
request.end_zone = 'frontyard'

# Get response
response = plan_path_client.call(request)

if response.success:
    # Navigate using route_ids
    for route_id in response.route_ids:
        self.navigate_route(route_id)
```

---

## Next Steps

1. **Record all routes** between your zones
2. **Test navigation** using recorded routes
3. **Integrate with mission planner** for autonomous multi-zone mowing
4. **Monitor GPS quality** and re-record routes as needed
5. **Implement battery-aware planning** (future enhancement)

---

## Documentation References

- **System Overview:** `MULTI_ZONE_GUIDE.md`
- **User Guide:** `ROUTE_RECORDING_GUIDE.md`
- **Best Practices:** `ROUTE_BEST_PRACTICES.md`
- **Architecture:** `MULTI_ZONE_ARCHITECTURE.txt`
- **Complete Summary:** `MULTI_ZONE_SYSTEM_COMPLETE.md`

---

## Support

For issues or questions:
1. Check logs: `ros2 node logs <node_name>`
2. Review documentation in project root
3. Test with: `./test_multi_zone_routes.sh`
4. Verify GPS with: `ros2 topic echo /gps/fix`

---

**Deployment Status:** ✅ READY FOR PRODUCTION

**System Version:** 1.0.0

**Last Updated:** February 11, 2024
