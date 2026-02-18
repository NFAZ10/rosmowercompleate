# GPS-Based Zone Recording Guide

## Overview

The Zone Recording System allows you to define mowing zones by physically walking or driving the robot around the perimeter. The system uses GPS positioning to automatically record waypoints, creating accurate zone boundaries without manual map clicking.

## Features

- **GPS-Based Recording**: Walk the robot around the perimeter to record zone boundaries
- **Intelligent Waypoint Sampling**: Only records when position changes significantly (>0.5m)
- **Polygon Simplification**: Automatically reduces waypoint count using Douglas-Peucker algorithm
- **Real-Time Area Calculation**: See zone area as you record
- **GPS Quality Monitoring**: Visual indicators for GPS accuracy (RTK, 3D fix, etc.)
- **Pause/Resume**: Handle obstacles or breaks during recording
- **Visual Odometry Ready**: Prepared for Isaac ROS stereo camera integration

---

## Quick Start

### 1. Access the Zone Recorder

Open your web browser and navigate to:
```
http://<robot-ip>:8080/zones/recorder
```

Or from the main control panel, click **Zone Recorder**.

### 2. Check GPS Quality

Before recording, ensure GPS has a good signal:
- **Green (Excellent)**: RTK Fixed - Best accuracy (1-2cm)
- **Yellow (Good)**: 3D Fix or RTK Float - Good accuracy (0.5-2m)
- **Orange (Poor)**: 2D Fix - Marginal accuracy (2-5m)
- **Red (No Fix)**: Cannot record

**Best practice**: Wait for green or yellow before starting.

### 3. Start Recording

1. Enter a descriptive **Zone Name** (e.g., "Front Yard", "Side Garden")
2. Set **Priority** (0-255, higher = mow first)
3. Click **▶️ Start Recording**

### 4. Walk the Perimeter

- Walk or drive the robot around the zone boundary
- Move at a steady pace (0.5-1 m/s)
- The system automatically samples waypoints every 0.5m
- Stay close to the actual boundary you want to define
- Watch the waypoint count increase in real-time

**Tips**:
- Walk just inside the boundary (e.g., 30cm from fence)
- Keep a consistent distance from obstacles
- Complete the full loop back to start

### 5. Handle Obstacles

If you encounter obstacles or need a break:
- Click **⏸️ Pause** to temporarily stop recording
- Navigate around obstacle or take your break
- Return to the boundary path
- Click **▶️ Resume** to continue

### 6. Stop and Save

When you return to your starting point:
- Click **⏹️ Stop & Save**
- The system will:
  - Auto-close the polygon (connect last to first point)
  - Simplify the polygon (remove redundant points)
  - Validate for self-intersections
  - Save to `/zones/<zone_name>.yaml`

---

## Understanding the Interface

### Status Indicator
- **IDLE**: Ready to record a new zone
- **RECORDING**: Currently recording waypoints
- **PAUSED**: Recording paused, no waypoints being saved

### GPS Quality Indicator
Shows current GPS fix quality and horizontal accuracy:
- **RTK Fixed**: 1-5cm accuracy (ideal)
- **RTK Float**: 10-50cm accuracy (very good)
- **3D Fix**: 1-3m accuracy (acceptable)
- **2D Fix**: 3-10m accuracy (poor, not recommended)
- **No Fix**: Cannot record

### Statistics Panel

**Waypoints**: Number of GPS positions recorded
- Typical zone: 20-100 waypoints before simplification
- After simplification: 10-30 waypoints

**Distance**: Total distance traveled (meters)
- Should roughly match zone perimeter
- Example: 20m x 15m rectangle ≈ 70m perimeter

**Area**: Estimated zone area (m²)
- Calculated in real-time using Shoelace formula
- Updated as you record waypoints
- Example: 20m x 15m ≈ 300m²

**GPS Quality**: Numeric quality value (0-4)
- 0 = No fix
- 1 = 2D fix
- 2 = 3D fix
- 3 = RTK float
- 4 = RTK fixed

---

## Best Practices

### Before Recording

1. **Check GPS Signal**
   - Wait for green (RTK) or yellow (3D fix) indicator
   - In tree cover, GPS may be degraded but still usable
   - Avoid recording in heavy rain or storms

2. **Plan Your Route**
   - Visualize the boundary before walking
   - Identify obstacles you'll need to navigate
   - Plan where to start/end (ideally same location)

3. **Check Battery**
   - Ensure robot has sufficient battery for full perimeter
   - Large zones may take 10-20 minutes to record
   - Pause recording if battery gets low

### During Recording

1. **Walking Speed**
   - Maintain steady pace: 0.5-1.0 m/s (slow walk)
   - Too fast: May miss corners
   - Too slow: Unnecessary waypoints, wasted time

2. **Boundary Accuracy**
   - Stay consistent distance from obstacles (e.g., 30cm from fence)
   - Mark starting point for easy reference
   - Use visual landmarks to stay on track

3. **Handling Corners**
   - Slow down slightly at corners
   - Make deliberate turns at sharp corners
   - The system will preserve corner waypoints during simplification

4. **Dealing with Obstacles**
   - **Temporary obstacles** (person, animal): Pause, wait, resume
   - **Permanent obstacles** (tree, rock): Walk around, but note location
   - **GPS dropout** (under trees): System will warn, keep moving

### After Recording

1. **Verify Zone**
   - Check waypoint count (typically 10-50 after simplification)
   - Verify estimated area makes sense
   - Review in zone manager for accuracy

2. **Test Mowing**
   - Start with low priority zone for testing
   - Monitor first mow to ensure boundary is correct
   - Adjust if robot ventures too close to obstacles

---

## Troubleshooting

### GPS Not Acquiring Fix

**Symptoms**: Red "No Fix" indicator, GPS quality = 0

**Solutions**:
- Ensure GPS antenna has clear view of sky
- Wait 2-5 minutes for GPS cold start
- Move away from buildings, trees, power lines
- Check GPS module connections
- Restart GPS node: `ros2 run gps_rtk gps_node`

### Poor GPS Accuracy

**Symptoms**: Orange "2D Fix" indicator, accuracy > 2.0m

**Solutions**:
- Wait for satellite acquisition (may take 5-10 min)
- Move to more open area
- Enable RTK corrections if available
- Consider using visual odometry (future Isaac ROS feature)

### Waypoints Not Recording

**Symptoms**: Distance traveled increases but waypoint count stays at 0

**Possible causes**:
- GPS accuracy below threshold (check accuracy value)
- Not moving enough (need >0.5m between points)
- Recording paused or not started

**Solutions**:
- Check GPS accuracy < 2.0m
- Verify status shows "RECORDING"
- Move faster or increase `waypoint_min_distance` parameter

### Polygon Self-Intersection Error

**Symptoms**: Warning message about self-intersection

**Cause**: Path crossed itself, creating invalid polygon

**Solutions**:
- Cancel recording and start over
- Walk more carefully to avoid crossing your path
- If intentional (complex boundary), split into multiple zones

### Zone Not Saving

**Symptoms**: "Stop & Save" succeeds but zone not in zone manager

**Solutions**:
- Check `/ws/zones/` or `zones/` directory for .yaml file
- Verify zone_manager service is running: `ros2 service list | grep zone`
- Check logs: `ros2 run rosmower zone_recorder.py` (look for errors)
- Restart zone_manager: `ros2 run rosmower zone_manager.py`

---

## Advanced Features

### Manual Parameter Tuning

Edit launch file parameters for specialized use cases:

```bash
ros2 launch rosmower zone_recorder.launch.py \
  waypoint_min_distance:=0.3 \
  simplification_tolerance:=0.2 \
  gps_accuracy_threshold:=3.0
```

**Parameters**:
- `waypoint_min_distance`: Minimum distance between waypoints (default: 0.5m)
  - Lower = more waypoints, higher accuracy
  - Higher = fewer waypoints, faster recording
  
- `simplification_tolerance`: Douglas-Peucker tolerance (default: 0.3m)
  - Lower = more waypoints retained, higher accuracy
  - Higher = fewer waypoints, simpler polygon
  
- `gps_accuracy_threshold`: Maximum GPS error to record (default: 2.0m)
  - Lower = only record with good GPS
  - Higher = record with degraded GPS (not recommended)

### API Integration

Programmatically control zone recording:

```bash
# Start recording
ros2 service call /zone/record/start rosmower_msgs/srv/StartZoneRecording \
  "{zone_name: 'my_zone', priority: 5}"

# Pause
ros2 service call /zone/record/control rosmower_msgs/srv/ControlZoneRecording \
  "{command: 0}"

# Resume
ros2 service call /zone/record/control rosmower_msgs/srv/ControlZoneRecording \
  "{command: 1}"

# Stop and save
ros2 service call /zone/record/stop rosmower_msgs/srv/StopZoneRecording \
  "{save_zone: true, auto_close: true, simplify: true}"
```

### RViz Visualization

Monitor recording in RViz:

1. Launch RViz: `ros2 run rviz2 rviz2`
2. Add display: **Path** → Topic: `/zone/record/waypoints`
3. Add display: **Polygon** → Topic: `/zone/record/polygon`
4. Watch waypoints appear in real-time as you record

---

## Isaac ROS Stereo Camera Integration (Future)

### Overview

When a stereo camera is installed, the system can use visual odometry to enhance GPS accuracy, especially in GPS-degraded environments (under trees, near buildings).

### Benefits
- Improved accuracy in GPS-denied areas
- Sub-meter positioning when GPS drifts
- Better corner and edge detection
- Consistent accuracy regardless of satellite visibility

### Integration Steps

1. **Install Stereo Camera**
   - Recommended: ZED 2i, RealSense D435i, or custom stereo rig
   - Mount front-center, 30-50cm high, tilted 10-15° down
   - Weatherproof enclosure for outdoor use

2. **Configure Isaac ROS**
   ```bash
   # Install Isaac ROS packages
   sudo apt install ros-humble-isaac-ros-visual-slam
   
   # Edit configuration
   nano src/rosmower/config/isaac_ros_stereo.yaml
   ```

3. **Enable Visual Odometry**
   ```yaml
   visual_odometry:
     enabled: true
   sensor_fusion:
     enabled: true
   ```

4. **Test Integration**
   ```bash
   # Launch with visual odometry
   ros2 launch rosmower zone_recorder.launch.py \
     visual_odometry_enabled:=true
   ```

5. **Verify in RViz**
   - Topic: `/visual_odometry/pose`
   - Should show smooth position estimates
   - Compare to GPS: `/gps/fix`

See `ISAAC_ROS_INSTALLATION.md` (coming soon) for detailed setup.

---

## Common Scenarios

### Small Residential Yard (100-500 m²)
- GPS: 3D fix usually sufficient
- Recording time: 5-10 minutes
- Waypoints: 30-60 before simplification
- Tips: One continuous loop, no pause needed

### Large Property with Multiple Zones (1000+ m²)
- GPS: RTK recommended for accuracy
- Recording time: 15-30 minutes per zone
- Waypoints: 60-120 before simplification
- Tips: Split into multiple zones, take breaks between

### Tree-Covered Area
- GPS: May degrade to 2D fix (orange indicator)
- Challenge: GPS drift, signal loss
- Solutions:
  - Record when satellites visible (early morning, late afternoon)
  - Use visual odometry (future feature)
  - Increase `gps_accuracy_threshold` to 3.0m
  - Walk slower for more waypoints

### Urban Setting (near buildings)
- GPS: May suffer from multipath errors
- Challenge: Signal bounce off buildings
- Solutions:
  - Record away from tall buildings
  - Enable RTK for multipath rejection
  - Use visual odometry for refinement

---

## Zone File Format

Recorded zones are saved as YAML files in `/zones/`:

```yaml
id: "front_yard"
name: "Front Yard"
priority: 10
frame_id: "map"
enabled: true
coverage_percent: 0.0
vertices:
  - {x: 0.0, y: 0.0, z: 0.0}
  - {x: 10.5, y: 0.2, z: 0.0}
  - {x: 10.3, y: 8.7, z: 0.0}
  - {x: 0.1, y: 8.5, z: 0.0}
```

**Note**: Coordinates are in local meters relative to first GPS point, not lat/lon.

---

## Safety Considerations

1. **Supervision**: Always supervise zone recording
2. **Obstacles**: Watch for moving obstacles (people, pets, vehicles)
3. **Terrain**: Be aware of slopes, holes, wet areas
4. **Weather**: Avoid recording in lightning, heavy rain
5. **Battery**: Don't let battery get critically low mid-recording
6. **Testing**: Always test-mow new zones in manual mode first

---

## Maintenance

### Regular Tasks
- Verify GPS antenna is clean and securely mounted
- Check GPS fix quality before each recording session
- Periodically re-record zones if terrain changes
- Update zone priorities as needed

### After Software Updates
- Rebuild workspace: `colcon build --packages-select rosmower rosmower_msgs`
- Test zone recording with short test zone
- Verify existing zones still load correctly

---

## Support & Resources

- **ROS Topics**: Use `ros2 topic list` to see zone recorder topics
- **Service Calls**: Use `ros2 service list` for available services
- **Logs**: Check `~/.ros/log/` for detailed error messages
- **Web UI**: Access at `http://<robot-ip>:8080/zones/recorder`

For issues or questions, check:
1. ROS2 logs: `ros2 node info /zone_recorder`
2. GPS status: `ros2 topic echo /gps/fix`
3. Zone recorder status: `ros2 topic echo /zone/record/status`

---

## Appendix: Douglas-Peucker Simplification

The zone recorder uses the Ramer-Douglas-Peucker algorithm to simplify recorded polygons while preserving shape.

### How It Works
1. Start with all recorded waypoints
2. Draw line from first to last point
3. Find waypoint farthest from this line
4. If distance > tolerance (0.3m), keep waypoint and split
5. Recursively simplify each segment
6. Result: Fewer waypoints, same shape

### Benefits
- Reduces waypoints by 50-70%
- Preserves corners and important features
- Faster path planning and mowing
- Smaller zone files

### Tuning
- Default tolerance: 0.3m (good for most cases)
- Lower (0.1-0.2m): More accurate, more waypoints
- Higher (0.5-1.0m): Simpler, fewer waypoints

**Example**:
- Before: 87 waypoints
- After: 23 waypoints
- Shape accuracy: ±0.3m

---

## Version History

- **v1.0** (2024-02): Initial GPS-based zone recording
- **v1.1** (TBD): Isaac ROS visual odometry integration
- **v1.2** (TBD): Multi-zone recording session support

---

**Last Updated**: February 2024  
**Maintained by**: ROS Mower Project
