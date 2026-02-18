# VESC Driver Integration Guide

## Overview
Complete integration guide for replacing hoverboard_bridge_node with VESC driver for dual VESC 6.7 motor controllers on the autonomous mower.

---

## Architecture Comparison

### Current System (Hoverboard Bridge)
```
/cmd_vel → hoverboard_bridge_node.py → Serial Protocol → Arduino Hoverboard Controller
```

### New System (VESC Driver)
```
/cmd_vel → vesc_driver_node (C++) → VESC Protocol → VESC ID 0 (USB) → CAN Bus → VESC ID 1
```

---

## Hardware Migration

### What You Need
1. ✅ 2× VESC 6.7 motor controllers (you have these)
2. ✅ CAN bus cable (CAN-H, CAN-L, GND between VESCs)
3. ✅ USB cable from Jetson to VESC ID 0
4. ✅ 24V LiFePO4 battery (you have this)
5. ✅ 2× 300W hoverboard BLDC motors with Hall sensors (you have these)

### Wiring Steps
1. **Power Connections**:
   - Connect 24V+ and GND from battery to both VESCs
   - Use appropriate gauge wire for 15A+ current

2. **Motor Connections** (VESC → Motor):
   - Phase A, B, C (three thick wires)
   - Hall sensor 5V, GND, H1, H2, H3 (five thin wires)

3. **CAN Bus** (VESC 0 → VESC 1):
   ```
   VESC 0 CAN-H  →  VESC 1 CAN-H
   VESC 0 CAN-L  →  VESC 1 CAN-L
   VESC 0 GND    →  VESC 1 GND
   ```

4. **USB Connection**:
   - Jetson USB → VESC ID 0 USB port

---

## VESC Tool Configuration

### Download VESC Tool
```bash
# On your laptop/desktop (not Jetson)
wget https://vesc-project.com/vesc_tool
chmod +x vesc_tool
./vesc_tool
```

### Configure VESC ID 0 (Left Motor)

1. **Connect**: USB to VESC 0, click "Autoconnect"
2. **Motor Wizard**:
   - Select "FOC" mode
   - Set current limits: Max 15A, Battery max 10A
   - Run motor detection wizard
   - Save motor configuration

3. **General Settings**:
   - Battery: LiFePO4, 24V (7S), cutoff 21V, max 29.2V
   - Motor max ERPM: 30000 (adjust based on motor specs)

4. **CAN Settings**:
   - Set CAN ID: **0**
   - Enable "CAN Forward" (to forward commands to VESC 1)
   - CAN Baud: 500 kbit/s

5. **Write Configuration**

### Configure VESC ID 1 (Right Motor)

1. **Connect**: Move USB to VESC 1
2. **Repeat Motor Wizard** (same as VESC 0)
3. **CAN Settings**:
   - Set CAN ID: **1**
   - CAN Baud: 500 kbit/s

4. **Write Configuration**

5. **Test CAN**: Reconnect to VESC 0, try controlling VESC 1 over CAN in VESC Tool

---

## Software Integration

### Step 1: Build VESC Driver
```bash
cd /mnt/nova_ssd/rosmowercompleate
colcon build --packages-select vesc_driver --symlink-install
source install/setup.bash
```

### Step 2: Update Docker (if using Docker)
Add to `Dockerfile.arm64`:
```dockerfile
# No additional dependencies needed - all standard C++ libs
```

Rebuild Docker:
```bash
./build-docker.sh
```

### Step 3: Modify launch_robot.launch.py

**Option A: Replace hoverboard_bridge** (recommended)
```python
# Comment out old hoverboard bridge
# hoverboard = Node(...)

# Add VESC driver
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource

vesc_driver = IncludeLaunchDescription(
    PythonLaunchDescriptionSource(
        os.path.join(get_package_share_directory('vesc_driver'), 'launch', 'vesc_driver.launch.py')
    ),
    launch_arguments={
        'serial_port': '/dev/ttyACM0',
        'wheel_radius': '0.0875',
        'wheel_separation': '0.52',
        'pole_pairs': '15',
        'left_vesc_can_id': '0',
        'right_vesc_can_id': '1',
        'max_rpm': '3000',
    }.items()
)

# In LaunchDescription, replace hoverboard_group with:
vesc_driver,
```

**Option B: Keep both for testing**
```python
# Add VESC driver alongside hoverboard
# Use different namespaces to avoid conflicts
```

### Step 4: Calibrate Wheel Parameters

Measure your actual robot:
```bash
# Wheel radius (measure diameter, divide by 2)
# Example: 175mm diameter = 0.0875m radius
wheel_radius = <measured_value>

# Wheel separation (measure center-to-center)
# Example: 520mm = 0.52m
wheel_separation = <measured_value>

# Motor pole pairs (check VESC Tool or motor specs)
# Hoverboard motors: typically 15
pole_pairs = <check_vesc_tool>
```

Update in launch file or config file.

### Step 5: Test Drive

```bash
# Launch robot
ros2 launch rosmower launch_robot.launch.py

# In another terminal, test drive
ros2 run teleop_twist_keyboard teleop_twist_keyboard

# Test straight line (verify both wheels spin)
# Test rotation (verify differential drive)
```

### Step 6: Verify Odometry

```bash
# Check joint states
ros2 topic echo /joint_states

# Check odometry (if enabled)
ros2 topic echo /odom

# Visualize in RViz
rviz2
# Add: TF, Odometry, LaserScan
```

---

## Parameter Tuning

### Wheel Calibration Test
```bash
# Drive straight 1 meter
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{linear: {x: 0.5}}" --once
# Measure actual distance traveled
# Adjust wheel_radius if needed

# Rotate 360 degrees
ros2 topic pub /cmd_vel geometry_msgs/msg/Twist "{angular: {z: 1.0}}" --once
# Measure actual rotation
# Adjust wheel_separation if needed
```

### ERPM Limits
If motors struggle or overheat:
```yaml
max_rpm: 2000  # Reduce from 3000
```

In VESC Tool, also check:
- Current limits (reduce if overheating)
- Battery current limits
- ERPM limits

---

## Troubleshooting

### Motors Don't Move
1. Check VESC power LED (should be green/blue)
2. Verify USB connection: `ls /dev/ttyACM*`
3. Check permissions: `sudo chmod 666 /dev/ttyACM0`
4. Check VESC Tool can control motors
5. Verify CAN bus wiring
6. Check ROS 2 logs: `ros2 topic echo /rosout`

### One Motor Works, Other Doesn't
1. Verify CAN bus wiring (CAN-H, CAN-L, GND)
2. Check VESC ID 1 is configured correctly
3. Test VESC 1 directly in VESC Tool
4. Verify CAN forwarding enabled on VESC 0

### Erratic Movement
1. Calibrate wheel_radius and wheel_separation
2. Check motor direction (may need to swap two motor wires)
3. Verify pole_pairs setting matches motor
4. Check Hall sensor detection in VESC Tool

### High CPU Usage
```yaml
control_rate: 20.0  # Reduce from 50
telemetry_rate: 5.0  # Reduce from 10
```

### Odometry Drift
1. Calibrate wheel parameters precisely
2. Check wheel slippage on ground
3. Verify motor pole pairs correct
4. Consider fusing with IMU using robot_localization EKF

---

## Performance Comparison

| Feature | Hoverboard Bridge | VESC Driver |
|---------|-------------------|-------------|
| Language | Python | C++ |
| Control Loop | ~50 Hz | 50 Hz (configurable) |
| Telemetry | Limited | Full VESC telemetry |
| Current Monitoring | No | Yes (per motor) |
| Fault Detection | No | Yes (VESC fault codes) |
| CAN Support | No | Yes (native) |
| Temperature Monitoring | No | Yes (FET + Motor) |
| Field-Oriented Control | No | Yes (FOC) |
| Efficiency | Lower | Higher (FOC) |

---

## Next Steps

1. **Test in Safe Environment**: Drive on blocks before ground testing
2. **Calibrate Parameters**: Fine-tune wheel radius/separation
3. **Integrate with Nav2**: Verify odometry works with navigation stack
4. **Add Safety Features**:
   - Emergency stop button
   - Tilt sensor (stop on tip-over)
   - Battery voltage monitoring (already in VESC)
5. **Monitor Temperatures**: Check VESC telemetry for overheating
6. **Tune Current Limits**: Optimize for your terrain (grass may need higher current)

---

## Advanced: Dual Motor Telemetry

Currently, the driver reads telemetry from VESC 0 only. To track both motors separately:

**Modify vesc_driver_node.cpp**:
```cpp
// Add second VESC state
VescState left_state_;
VescState right_state_;

// In telemetry loop, track responses separately
// Parse CAN responses to distinguish VESC ID 0 vs 1
```

Or use separate VESC driver instances (one per VESC).

---

## Rollback Plan

If issues arise, revert to hoverboard bridge:

1. Uncomment hoverboard_bridge in launch file
2. Comment out vesc_driver
3. Rebuild: `colcon build --packages-select rosmower`
4. Relaunch: `ros2 launch rosmower launch_robot.launch.py`

---

## Support

- **VESC Forum**: https://vesc-project.com/forum
- **VESC Documentation**: https://vesc-project.com/docs
- **ROS 2 Humble Docs**: https://docs.ros.org/en/humble/

---

**Status**: Ready for integration  
**Tested**: Hardware detection verified  
**Next**: Build and test with actual VESCs
