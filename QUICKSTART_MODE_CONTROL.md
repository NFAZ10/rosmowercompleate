# Quick Start: Mode Control

## What This Does
Control your ROS mower's operational mode (IDLE, CHARGING, MOWING, FULL) at runtime via a web interface or command line - no need to restart!

## Quick Test

1. **Launch the robot**:
   ```bash
   ./docker-helper.sh launch
   ```

2. **Open web interface**:
   - Open file in browser: `src/rosmower/web/mode_control.html`
   - Connect to: `ws://localhost:9090` (or your robot's IP)

3. **Click a mode button** - the robot will switch modes instantly!

## What Each Mode Does

| Mode | Motors | Sensors | GPS | LIDAR | Camera | Use Case |
|------|--------|---------|-----|-------|--------|----------|
| 💤 IDLE | ❌ | ❌ | ❌ | ❌ | ❌ | Parked/standby |
| 🔋 CHARGING | ❌ | ✅ | ❌ | ❌ | ❌ | On charger |
| 🌱 MOWING | ✅ | ✅ | ✅ | ✅ | ✅ | Autonomous mowing |
| ⚡ FULL | ✅ | ✅ | ✅ | ✅ | ✅ | Testing/dev |

## Command Line Alternative
```bash
ros2 topic pub /robot_mode_cmd std_msgs/String "data: 'mowing'" --once
```

See `src/rosmower/MODE_CONTROL_README.md` for full documentation.
