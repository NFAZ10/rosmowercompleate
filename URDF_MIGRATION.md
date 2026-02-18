# URDF Migration Summary

## Overview
Migrated from modular URDF structure (robot.urdf.xacro with multiple includes) to a comprehensive, self-contained URDF file (rosmower.urdf.xacro) that accurately models the robot's physical structure.

## New URDF Features

### Frame Structure
- **Base chassis**: Modeled as aluminum extrusion rails (40mm x 40mm)
  - 2 longitudinal rails (600mm length)
  - 3 cross members: front, middle, rear (300mm width each)
  - Each rail calculated with proper mass and inertia based on aluminum density (2700 kg/m³)
  - `base_link` at chassis center
  - `base_footprint` at ground level for Nav2 compatibility

### Drive System
- **Front drive wheels**: 27-inch diameter (0.34290m radius)
  - Differential drive configuration
  - Continuous joints: `left_wheel_joint`, `right_wheel_joint`
  - Track width: 0.35m (chassis width + offset)
  - Includes transmissions for ros2_control integration

### Rear Caster
- **8-inch swivel caster**: Two-joint assembly
  - `caster_swivel_joint`: Continuous rotation (yaw axis)
  - `caster_wheel_joint`: Wheel spin (pitch axis)
  - Positioned at rear center with proper ground contact

### Sensors

#### Stereo Cameras
- **Frame IDs**: `left_camera_link`, `right_camera_link`
- **Optical frames**: `left_camera_optical_frame`, `right_camera_optical_frame`
  - REP-103 compliant (Z forward, X right, Y down)
- **Spacing**: 3 inches (0.0762m) apart
- **Position**: Front center, slightly elevated

#### LIDAR
- **Frame ID**: `lidar_link`
- **Position**: Centered, 100mm above drive wheel height
- **Type**: 360-degree scanning

## Launch File Updates

### 1. `rsp.launch.py` (Robot State Publisher)
**Changes:**
- Updated to load `rosmower.urdf.xacro` instead of `robot.urdf.xacro`
- Added launch arguments for `use_sim_time` and `use_ros2_control`
- Made parameters dynamic (not hardcoded)

### 2. `launch_robot.launch.py` (Main Robot Launch)
**Changes:**
- Updated RPLIDAR frame_id: `laser_frame` → `lidar_link`
- Updated stereo camera frame_ids: 
  - Added separate `left_frame_id` and `right_frame_id` parameters
  - Changed from generic `stereo_camera` to `left_camera_link` / `right_camera_link`
- **Removed** static transform publishers for sensors (now defined in URDF):
  - ❌ `laser_to_base_tf` (0.20, 0, 0.25 offset)
  - ❌ `left_camera_tf` (0.15, 0.06, 0.15 offset)
  - ❌ `right_camera_tf` (0.15, -0.06, 0.15 offset)

### 3. `rplidar.launch.py` (Standalone LIDAR Launch)
**Changes:**
- Updated default frame_id: `laser_frame` → `lidar_link`

## Migration Benefits

### Accuracy
- ✅ Proper physical dimensions based on actual hardware specs
- ✅ Accurate inertial properties for physics simulation
- ✅ Correct sensor placement matching hardware layout

### Maintainability
- ✅ Single source of truth for robot geometry
- ✅ No redundant static transforms to maintain
- ✅ Easier to visualize in RViz (all frames from URDF)

### Compatibility
- ✅ Nav2-ready with proper `base_footprint` frame
- ✅ REP-103 compliant camera optical frames
- ✅ ros2_control transmissions for future motor integration
- ✅ Gazebo-compatible inertial properties

## Frame Hierarchy

```
base_footprint (ground level)
└── base_link (chassis center at drive wheel height)
    ├── left_rail
    ├── right_rail
    ├── front_cross
    ├── rear_cross
    ├── middle_cross
    ├── left_wheel
    ├── right_wheel
    ├── caster_swivel
    │   └── caster_wheel
    ├── left_camera_link
    │   └── left_camera_optical_frame
    ├── right_camera_link
    │   └── right_camera_optical_frame
    └── lidar_link
```

## Validation

Run the provided test script to validate URDF:
```bash
./test_urdf.sh
```

This will:
1. Process Xacro to URDF
2. Validate with `check_urdf`
3. List all links and joints
4. Generate TF tree visualization (if tools available)

## Next Steps

### Immediate
1. ✅ Build workspace: `colcon build --packages-select rosmower`
2. ✅ Source: `source install/setup.bash`
3. ✅ Test launch: `ros2 launch rosmower rsp.launch.py`
4. ✅ Visualize in RViz: `ros2 run rviz2 rviz2`
   - Add RobotModel display
   - Add TF display to verify frame tree

### Optional Enhancements
- [ ] Tune wheel parameters (`wheel_radius`, `wheel_separation`) based on odometry testing
- [ ] Add collision meshes for better obstacle avoidance
- [ ] Add visual meshes for realistic rendering
- [ ] Configure ros2_control hardware interface for motor controllers
- [ ] Add Gazebo plugins for simulation testing

## Backward Compatibility

**Breaking changes:**
- Sensor frame IDs changed (update any hardcoded references)
- Static transforms removed (now in URDF)

**If you need old behavior:**
- Old URDF files preserved: `robot.urdf.xacro`, `robot_core.xacro`, etc.
- To revert: Change `rsp.launch.py` back to `robot.urdf.xacro`

## Camera Node Configuration

**Important:** If your `stereo_camera_node` uses a single `frame_id` parameter instead of separate `left_frame_id` and `right_frame_id`, you may need to update the camera driver code or revert to bridge frames.

Current configuration assumes the camera driver supports:
```python
'left_frame_id': 'left_camera_link',
'right_frame_id': 'right_camera_link',
```

If not supported, you can add bridge transforms back temporarily.

---

**Questions or issues?** Test incrementally:
1. Start with just robot state publisher
2. Add sensors one at a time
3. Verify TF tree with: `ros2 run tf2_tools view_frames`
