cmake_minimum_required(VERSION 3.5)
project(rosmower)

# C standards
if(NOT CMAKE_C_STANDARD)
  set(CMAKE_C_STANDARD 99)
endif()
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()
if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Core
find_package(ament_cmake REQUIRED)

# ROS 2 deps for the Python nodes
find_package(rclpy REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(mavros_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_msgs REQUIRED)
find_package(std_srvs REQUIRED)

# Install resources (your existing assets)
install(
  DIRECTORY config description launch worlds web
  DESTINATION share/${PROJECT_NAME}
)

# Install Python executables
install(PROGRAMS
  scripts/blade_controller.py
  scripts/hoverboard_bridge_node.py
  scripts/lidar_scan_guard.py
  scripts/imu_bridge.py
  scripts/rplidar_motor_control.py
  scripts/battery_splitter.py
  scripts/battery_monitor.py
  scripts/cmd_vel_gate.py
  scripts/zone_manager.py
  scripts/zone_recorder.py
  scripts/relay_control_node.py
  scripts/vl53_bridge.py
  scripts/tof_to_scan.py
  scripts/tof_guard.py
  scripts/image_flip_node.py
  scripts/mode_manager.py
  DESTINATION lib/${PROJECT_NAME}
)

# Build and install C++ rplidar motor control node (if needed in future)
# find_package(rclcpp REQUIRED)
# find_package(sensor_msgs REQUIRED)
# find_package(std_srvs REQUIRED)

# Note: No C++ targets to build currently
# Uncomment install(TARGETS...) when C++ nodes are added

# Testing
if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

# <<< MUST BE LAST >>>
ament_package()
