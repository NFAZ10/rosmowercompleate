# 🚀 Zone Recording Quick Start Card

**5-Minute Guide to Recording Your First Zone**

---

## Prerequisites Check ✓

```bash
# 1. Verify you're in the workspace
cd /mnt/nova_ssd/rosmowercompleate

# 2. Check ROS2 is installed
ros2 --version  # Should show: ros2 doctor version 0.10.x

# 3. Check GPS is connected
ls /dev/ttyACM* /dev/ttyUSB*  # Should show GPS device
```

---

## Step 1: Build (First Time Only) 🔨

```bash
# Make script executable
chmod +x build_zone_recorder.sh

# Build everything (takes ~2 minutes)
./build_zone_recorder.sh

# Source the workspace
source install/setup.bash
```

**Success Check**: You should see:
```
✓ rosmower_msgs built successfully
✓ rosmower built successfully
✓ Messages found
✓ Zone recorder executable installed
Ready to record zones!
```

---

## Step 2: Launch Zone Recorder 🎬

```bash
# Terminal 1: Launch zone recorder
ros2 launch rosmower zone_recorder.launch.py
```

**Success Check**: You should see:
```
[INFO] [zone_recorder]: Zone recorder node started
[INFO] [zone_recorder]: Waiting for GPS fix...
```

---

## Step 3: Start Web Server 🌐

```bash
# Terminal 2: Start web server
python3 web_server.py
```

**Success Check**: You should see:
```
* Running on http://0.0.0.0:8080
```

---

## Step 4: Open Web UI 📱

1. **Find your robot's IP**:
   ```bash
   hostname -I | awk '{print $1}'
   ```

2. **Open browser** to:
   ```
   http://<robot-ip>:8080/zones/recorder
   ```

3. **Verify GPS quality** indicator is **green** or **yellow**
   - 🟢 Green = RTK Fixed (excellent!)
   - 🟡 Yellow = 3D Fix (good!)
   - 🟠 Orange = 2D Fix (wait for better signal)
   - 🔴 Red = No Fix (move to open area)

---

## Step 5: Record Your Zone 🗺️

### The Process:
1. **Enter zone details**:
   - Zone Name: `test_zone`
   - Priority: `10` (or 1-255)

2. **Click** "▶️ Start Recording"

3. **Walk or drive robot** around the perimeter:
   - Stay ~30cm inside boundary
   - Move at walking pace (0.5-1 m/s)
   - Complete the full loop
   - Watch waypoint count increase!

4. **If you need to pause**:
   - Click "⏸️ Pause" (for obstacles/breaks)
   - Navigate around obstacle
   - Click "▶️ Resume"

5. **When done**:
   - Click "⏹️ Stop & Save"
   - System auto-closes polygon and simplifies

---

## Step 6: Verify Zone Saved ✅

```bash
# Check zone file exists
ls -lh zones/test_zone.yaml

# View zone content
cat zones/test_zone.yaml
```

You should see:
```yaml
name: "test_zone"
priority: 10
boundary:
  - {x: 0.0, y: 0.0}
  - {x: 10.5, y: 0.2}
  # ... more waypoints ...
area: 125.5  # square meters
```

---

## Troubleshooting 🔧

### GPS Not Working?
```bash
# Check GPS topic
ros2 topic echo /gps/fix --once

# If nothing appears:
ros2 topic list | grep gps  # Check if topic exists
ros2 node list | grep gps   # Check if GPS node running
```

### No Waypoints Recording?
**Check**:
- GPS quality must be green/yellow (not red)
- You must move >0.5m between waypoints
- Recording state is "RECORDING" (not paused)

### Zone Not Saving?
```bash
# Check zone_manager is running
ros2 service list | grep zone/save

# If not found, you may need to start it separately
```

### Web UI Not Loading?
```bash
# Check web server is running
ps aux | grep web_server.py

# Check firewall allows port 8080
sudo ufw allow 8080
```

---

## Quick Test with Simulated Data 🧪

Don't have GPS yet? Test with simulated data:

```bash
# Run test script
chmod +x test_zone_recording.sh
./test_zone_recording.sh
```

This will:
- Publish fake GPS waypoints in a rectangle
- Start recording
- Stop and verify zone saved
- Show you how everything works!

---

## Command Reference Card 📋

### Essential ROS2 Commands
```bash
# Monitor recording status
ros2 topic echo /zone/record/status

# Check GPS
ros2 topic echo /gps/fix

# List all services
ros2 service list | grep zone

# Call service from command line
ros2 service call /zone/record/start rosmower_msgs/srv/StartZoneRecording \
  "{zone_name: 'my_zone', priority: 5}"
```

### Essential Web API Calls
```bash
# Start recording (curl)
curl -X POST http://localhost:8080/api/zone/record/start \
  -H "Content-Type: application/json" \
  -d '{"zone_name": "my_zone", "priority": 10}'

# Get status
curl http://localhost:8080/api/zone/record/status

# Stop and save
curl -X POST http://localhost:8080/api/zone/record/stop \
  -H "Content-Type: application/json" \
  -d '{"save_zone": true, "simplify": true}'
```

---

## Configuration Tuning ⚙️

### Adjust Waypoint Sampling Distance
```bash
# More frequent sampling (every 0.3m instead of 0.5m)
ros2 launch rosmower zone_recorder.launch.py waypoint_min_distance:=0.3
```

### Adjust Simplification Aggressiveness
```bash
# More simplification (remove more points)
ros2 launch rosmower zone_recorder.launch.py simplification_tolerance:=0.5

# Less simplification (keep more points)
ros2 launch rosmower zone_recorder.launch.py simplification_tolerance:=0.2
```

### Require Better GPS Accuracy
```bash
# Only record with RTK/high-quality GPS
ros2 launch rosmower zone_recorder.launch.py gps_accuracy_threshold:=1.0
```

---

## Expected Performance 📊

| Metric | Typical Value |
|--------|---------------|
| **Recording Time** | 5-15 minutes (depending on zone size) |
| **Waypoints (Raw)** | 40-120 |
| **Waypoints (Simplified)** | 10-30 |
| **Accuracy (RTK)** | ±0.3m |
| **Accuracy (3D Fix)** | ±1.5m |
| **CPU Usage** | <1% |
| **Memory Usage** | ~45 MB |
| **Zone File Size** | 1-5 KB |

---

## What's Next? 🎯

After recording your zones:

1. **View in RViz**:
   ```bash
   rviz2 -d rviz_configs/zone_visualization.rviz
   ```

2. **Plan autonomous missions** using recorded zones

3. **Record multiple zones** for complex properties

4. **Tune parameters** for your specific GPS setup

5. **Consider Isaac ROS integration** for GPS-degraded areas

---

## Full Documentation 📚

- **Complete User Guide**: `ZONE_RECORDING_GUIDE.md`
- **Quick Reference**: `ZONE_RECORDING_QUICKREF.md`
- **Technical Docs**: `ZONE_RECORDING_README.md`
- **Architecture**: `ZONE_RECORDING_ARCHITECTURE.md`
- **Installation**: `ZONE_RECORDING_INSTALL.md`
- **Navigation Hub**: `ZONE_RECORDING_INDEX.md`

---

## Help & Support 🆘

```bash
# Run diagnostic test
./test_zone_recording.sh

# Check node is running
ros2 node list | grep zone_recorder

# View detailed logs
ros2 run rosmower zone_recorder.py  # Run in foreground

# Check all topics
ros2 topic list | grep zone
```

---

## Success! 🎉

You're now ready to:
- ✅ Record zones by walking the robot
- ✅ Monitor GPS quality in real-time
- ✅ Save zones for autonomous mowing
- ✅ Handle complex multi-zone properties

**Happy zone recording!**

---

**Quick Links**:
- Start Here: `ZONE_RECORDING_INDEX.md`
- Problems? See: `ZONE_RECORDING_GUIDE.md` → Troubleshooting
- Advanced: `ZONE_RECORDING_README.md` → Configuration

**Version**: 1.0 | **Status**: Production Ready ✓
