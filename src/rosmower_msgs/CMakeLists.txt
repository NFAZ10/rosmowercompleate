cmake_minimum_required(VERSION 3.8)
project(rosmower_msgs)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# Find dependencies
find_package(ament_cmake REQUIRED)
find_package(std_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(rosidl_default_generators REQUIRED)

# Generate messages and services
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/Zone.msg"
  "msg/ZoneArray.msg"
  "msg/BatteryStatus.msg"
  "msg/Mission.msg"
  "msg/ZoneRecordingStatus.msg"
  "msg/Route.msg"
  "msg/RouteArray.msg"
  "msg/ZoneGraphNode.msg"
  "msg/ZoneGraphEdge.msg"
  "msg/ZoneGraph.msg"
  "msg/RouteRecordingStatus.msg"
  "srv/SaveZone.srv"
  "srv/LoadZone.srv"
  "srv/ListZones.srv"
  "srv/DeleteZone.srv"
  "srv/StartZoneRecording.srv"
  "srv/StopZoneRecording.srv"
  "srv/ControlZoneRecording.srv"
  "srv/StartRouteRecording.srv"
  "srv/StopRouteRecording.srv"
  "srv/ControlRouteRecording.srv"
  "srv/PlanRoute.srv"
  "srv/UpdateZoneMetadata.srv"
  "srv/GetZoneGraph.srv"
  "srv/ListRoutes.srv"
  "srv/DeleteRoute.srv"
  DEPENDENCIES std_msgs geometry_msgs sensor_msgs builtin_interfaces
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()
