# Copilot Instructions for rosmower Workspace

## Overview
This workspace is a ROS 2-based robotics stack for a mower robot, integrating multiple hardware and software components. The architecture is modular, with each major function (e.g., motor control, sensor integration, navigation) in its own ROS 2 package under `src/`. Key packages include `rosmower`, `diffdrive_arduino`, `sllidar_ros2`, `serial`, and `test_mavros`.

## Key Components & Data Flow
- **rosmower**: Main robot logic, launch files, and scripts (see `rosmower/scripts/` for sensor/motor nodes, e.g., `tof_guard.py`, `hoverboard_bridge_node.py`).
- **diffdrive_arduino**: Interfaces ROS 2 with Arduino-based motor controllers.
- **sllidar_ros2**: LIDAR integration for mapping and navigation.
- **serial**: Provides cross-platform serial communication utilities.
- **test_mavros**: Contains hand-tests for MAVROS/FCU integration.

Data flows between nodes via ROS 2 topics, with launch files in `rosmower/launch/` orchestrating multi-node bringup. Hardware device paths are often set via launch arguments (see `launch_robot.launch.py`).

## Developer Workflows
- **Build**: Use [colcon](https://colcon.readthedocs.io/) for building:  
  `colcon build --symlink-install`
- **Source environment**:  
  `source install/setup.bash`
- **Run**: Launch the robot stack with:  
  `ros2 launch rosmower launch_robot.launch.py`
- **Testing**: Manual and hand-tests are in `test_mavros/`. Automated tests are limited.
- **Debugging**: Use ROS 2 CLI tools (`ros2 topic echo`, `ros2 node list`, etc.) and check device paths in launch files.

## Project Conventions
- **Python nodes**: Scripts in `rosmower/scripts/` are ROS 2 nodes, using rclpy and parameterized via ROS params.
- **Device paths**: Serial and sensor device paths are hardcoded or settable via launch arguments.
- **Naming**: Topic and frame names are explicit and descriptive (e.g., `tof/front_left/range`).
- **Launch files**: All major bringup is via Python launch files in `rosmower/launch/`.
- **No monolithic main**: Each hardware or logic component is a separate node/script.

## Integration & External Dependencies
- **ROS 2**: All packages are ROS 2 (foxy/humble/rolling supported, see individual package READMEs).
- **Arduino**: Motor control via Arduino running `ros_arduino_bridge` firmware.
- **LIDAR**: SLAMTEC LIDAR supported via `sllidar_ros2`.
- **MAVROS**: For PX4/FCU integration, see `test_mavros/` and related launch files.

## Examples
- To add a new sensor node, follow the pattern in `rosmower/scripts/tof_guard.py` (parameterized, publishes sensor_msgs, launched via launch file).
- To change device paths, edit the relevant launch file (e.g., `launch_robot.launch.py`).

## References
- See each package's `README.md` for hardware-specific setup and usage.
- Launch files: `rosmower/launch/`
- Main scripts: `rosmower/scripts/`

---
For questions or unclear conventions, check the launch files and scripts for examples, or ask for clarification.
