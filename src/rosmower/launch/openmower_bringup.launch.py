"""
openmower_bringup.launch.py

Bridges our existing robot hardware stack (vesc_driver, gps_rtk, icm20948_imu_driver)
with the open_mower_next navigation stack (map_server, map_recorder, EKF localization, Nav2).

What this launch file does:
  - Reads OM_DATUM_LAT / OM_DATUM_LONG env vars (defaults to current robot position)
  - Starts open_mower_next localization (robot_localization EKF + navsat_transform)
  - Starts open_mower_next map_server_node and map_recorder
  - Starts open_mower_next Nav2 stack
  - Does NOT start: controller_manager, micro_ros_agent, ublox_f9p, joystick
    (those are handled by launch_robot.launch.py already)

Topic mapping from our stack to open_mower_next expectations:
  /odom             → used as odom0 in robot_localization EKF (patched in yaml)
  /imu/data_raw     → remapped to imu/data_raw in ekf_node (done in localization.launch.py)
  /gps/fix          → navsat_transform subscribes to /gps/fix by default
"""

import os
from launch import LaunchDescription
from launch.actions import (
    IncludeLaunchDescription,
    DeclareLaunchArgument,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    om_share = get_package_share_directory("open_mower_next")

    # --- GPS datum: use env vars, fall back to robot's known position ---
    datum_lat = os.getenv("OM_DATUM_LAT", "41.181658")
    datum_lon = os.getenv("OM_DATUM_LONG", "-74.559870")
    map_path = os.getenv("OM_MAP_PATH", "/ws/zones/mowing_map.geojson")

    use_sim_time = LaunchConfiguration("use_sim_time", default="false")

    # Ensure env vars are set for child launch files that read them
    set_datum_lat = SetEnvironmentVariable("OM_DATUM_LAT", datum_lat)
    set_datum_lon = SetEnvironmentVariable("OM_DATUM_LONG", datum_lon)
    set_map_path = SetEnvironmentVariable("OM_MAP_PATH", map_path)

    # --- robot_localization EKF + navsat_transform ---
    # localization.launch.py also starts map_server_node, map_recorder, docking_helper
    localization = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(om_share, "launch", "localization.launch.py")
        ),
        launch_arguments={
            "use_sim_time": "false",
            "autostart": "true",
        }.items(),
    )

    # --- Nav2 stack (planner, controller, bt_navigator, etc.) ---
    nav2 = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(om_share, "launch", "nav2.launch.py")
        ),
        launch_arguments={
            "use_sim_time": "false",
            "autostart": "true",
        }.items(),
    )

    # --- Foxglove bridge for visualization in Foxglove Studio ---
    # Wrapped in a try since foxglove_bridge might not be installed everywhere
    try:
        from launch_xml.launch_description_sources import XMLLaunchDescriptionSource
        foxglove = IncludeLaunchDescription(
            XMLLaunchDescriptionSource(
                os.path.join(
                    get_package_share_directory("foxglove_bridge"),
                    "launch",
                    "foxglove_bridge_launch.xml",
                )
            ),
        )
    except Exception:
        foxglove = None

    actions = [
        set_datum_lat,
        set_datum_lon,
        set_map_path,
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="false",
            description="Use simulation clock",
        ),
        # Small delay lets our hardware nodes (vesc, GPS, IMU) come up first
        TimerAction(period=5.0, actions=[localization]),
        TimerAction(period=8.0, actions=[nav2]),
    ]

    if foxglove is not None:
        actions.append(foxglove)

    return LaunchDescription(actions)
