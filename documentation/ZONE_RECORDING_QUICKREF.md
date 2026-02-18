# Zone Recording Quick Reference

## Quick Start Commands

### Start Zone Recorder Node
```bash
ros2 launch rosmower zone_recorder.launch.py
```

### Access Web UI
```
http://<robot-ip>:8080/zones/recorder
```

### Check Status
```bash
ros2 topic echo /zone/record/status
```

---

## ROS2 Service Calls

### Start Recording
```bash
ros2 service call /zone/record/start rosmower_msgs/srv/StartZoneRecording \
  "{zone_name: 'my_zone', priority: 5, use_visual_odometry: false}"
```

### Stop and Save
```bash
ros2 service call /zone/record/stop rosmower_msgs/srv/StopZoneRecording \
  "{save_zone: true, auto_close: true, simplify: true, simplification_tolerance: 0.3}"
```

### Pause Recording
```bash
ros2 service call /zone/record/control rosmower_msgs/srv/ControlZoneRecording "{command: 0}"
```

### Resume Recording
```bash
ros2 service call /zone/record/control rosmower_msgs/srv/ControlZoneRecording "{command: 1}"
```

### Cancel Recording
```bash
ros2 service call /zone/record/control rosmower_msgs/srv/ControlZoneRecording "{command: 2}"
```

---

## API Endpoints

### Start Recording (HTTP)
```bash
curl -X POST http://localhost:8080/api/zone/record/start \
  -H "Content-Type: application/json" \
  -d '{"zone_name": "front_yard", "priority": 10}'
```

### Stop Recording (HTTP)
```bash
curl -X POST http://localhost:8080/api/zone/record/stop \
  -H "Content-Type: application/json" \
  -d '{"save_zone": true, "auto_close": true, "simplify": true}'
```

### Get Status (HTTP)
```bash
curl http://localhost:8080/api/zone/record/status
```

---

## Monitoring Topics

### Recording Status
```bash
ros2 topic echo /zone/record/status
```

### Waypoints Path
```bash
ros2 topic echo /zone/record/waypoints
```

### Polygon
```bash
ros2 topic echo /zone/record/polygon
```

### State String
```bash
ros2 topic echo /zone/record/state
```

### GPS Fix
```bash
ros2 topic echo /gps/fix
```

---

## Visualization in RViz

```bash
# Launch RViz
ros2 run rviz2 rviz2

# Add displays:
# - Path: /zone/record/waypoints (green)
# - Polygon: /zone/record/polygon (yellow)
# - NavSatFix: /gps/fix
```

---

## GPS Quality Codes

| Code | Status | Accuracy | Recording |
|------|--------|----------|-----------|
| 0 | No Fix | >10m | ❌ No |
| 1 | 2D Fix | 3-10m | ⚠️ Poor |
| 2 | 3D Fix | 1-3m | ✅ Good |
| 3 | RTK Float | 0.1-0.5m | ✅ Very Good |
| 4 | RTK Fixed | 0.01-0.05m | ✅ Excellent |

---

## Default Parameters

```yaml
waypoint_min_distance: 0.5      # meters between waypoints
simplification_tolerance: 0.3   # Douglas-Peucker tolerance
gps_accuracy_threshold: 2.0     # max GPS error to record
frame_id: "map"                 # TF frame
publish_rate: 2.0               # status update Hz
```

---

## Typical Recording Session

1. **Prepare**: Check GPS quality (wait for green/yellow)
2. **Start**: Click "Start Recording" or call service
3. **Walk**: Move around perimeter at 0.5-1 m/s
4. **Monitor**: Watch waypoint count increase
5. **Pause**: If needed, pause for obstacles
6. **Complete**: Return to start point
7. **Save**: Click "Stop & Save"
8. **Verify**: Check zone in zone manager

---

## File Locations

- **Zones**: `/ws/zones/` or `zones/`
- **Node**: `src/rosmower/scripts/zone_recorder.py`
- **Web UI**: `src/rosmower/web/zone_recorder.html`
- **Config**: `src/rosmower/config/isaac_ros_stereo.yaml`
- **Launch**: `src/rosmower/launch/zone_recorder.launch.py`

---

## Common Issues

### No waypoints recording
- Check GPS accuracy < 2.0m
- Verify status is "RECORDING"
- Ensure moving >0.5m between points

### GPS quality poor
- Move to open area
- Wait 5-10 minutes for satellite lock
- Enable RTK corrections

### Zone not saving
- Check zone_manager is running
- Verify zones directory permissions
- Check logs for errors

---

## Troubleshooting Commands

### Check Node Status
```bash
ros2 node list | grep zone_recorder
ros2 node info /zone_recorder
```

### Check Messages Built
```bash
ros2 interface list | grep ZoneRecording
```

### View Logs
```bash
ros2 run rosmower zone_recorder.py  # foreground for logs
```

### Test GPS
```bash
ros2 topic hz /gps/fix
ros2 topic echo /gps/fix --once
```

### List Services
```bash
ros2 service list | grep zone
```

---

## Performance Tips

### For Best Accuracy
- Use RTK GPS (quality 4)
- Walk slowly (0.5 m/s)
- Lower simplification tolerance (0.2m)
- Record in good weather

### For Speed
- Accept 3D fix (quality 2)
- Walk faster (1 m/s)
- Higher simplification tolerance (0.5m)
- Fewer waypoints needed

### For Complex Boundaries
- More waypoints (lower min_distance: 0.3m)
- Lower simplification (0.2m)
- Walk slowly around corners
- Pause for obstacles

---

## Build Commands

### Build Messages Only
```bash
colcon build --packages-select rosmower_msgs
source install/setup.bash
```

### Build Zone Recorder
```bash
colcon build --packages-select rosmower
source install/setup.bash
```

### Build All
```bash
colcon build
source install/setup.bash
```

---

## Docker Commands

### Build Docker Image
```bash
./build-docker.sh
```

### Start Container
```bash
docker-compose up -d
```

### Check Logs
```bash
docker logs rosmower_robot
```

### Execute in Container
```bash
docker exec -it rosmower_robot bash
source /opt/ros/humble/setup.bash
ros2 launch rosmower zone_recorder.launch.py
```

---

## Safety Checklist

- [ ] GPS has good fix (green/yellow)
- [ ] Battery >30%
- [ ] Clear path around perimeter
- [ ] No moving obstacles
- [ ] Weather conditions acceptable
- [ ] Supervisor present
- [ ] Emergency stop accessible

---

## Keyboard Shortcuts (Web UI)

- **Enter**: Start recording (when name field focused)
- **Space**: Pause/Resume (when button focused)
- **Esc**: Cancel (with confirmation)

---

## Expected Results

### Small Yard (100-300 m²)
- Recording time: 5-10 minutes
- Waypoints before: 30-60
- Waypoints after: 10-25
- Perimeter: 40-70m

### Medium Yard (300-1000 m²)
- Recording time: 10-20 minutes
- Waypoints before: 60-120
- Waypoints after: 20-40
- Perimeter: 70-130m

### Large Property (1000+ m²)
- Recording time: 20-40 minutes
- Waypoints before: 120-250
- Waypoints after: 30-80
- Perimeter: 130-250m

---

## Support Resources

- **User Guide**: `ZONE_RECORDING_GUIDE.md`
- **Technical Docs**: `ZONE_RECORDING_README.md`
- **Test Script**: `./test_zone_recording.sh`
- **Isaac ROS Config**: `config/isaac_ros_stereo.yaml`

---

**Quick Tip**: Always test new zones in manual mode before autonomous mowing!

---

**Version**: 1.0 | **Last Updated**: Feb 2024
