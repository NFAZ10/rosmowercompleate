#!/usr/bin/env python3
"""
openmower_mission launch file — starts all OpenMowerNext-inspired mission nodes:
  - coverage_path_generator  (boustrophedon coverage planning)
  - mission_executor         (full autonomous mow state machine)
  - dock_manager             (dock position + return navigation)
  - zone_costmap_publisher   (exclusion/nav zones → Nav2 costmap)
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_share = FindPackageShare('openmower_mission')
    config_file = PathJoinSubstitution([pkg_share, 'config', 'mission_params.yaml'])

    return LaunchDescription([
        # ── Launch arguments ──────────────────────────────────────────────
        DeclareLaunchArgument(
            'stripe_width_m', default_value='0.28',
            description='Mower deck width in meters (stripe spacing)'
        ),
        DeclareLaunchArgument(
            'overlap_m', default_value='0.04',
            description='Stripe overlap in meters'
        ),
        DeclareLaunchArgument(
            'approach_angle_deg', default_value='0.0',
            description='Coverage stripe direction in degrees'
        ),
        DeclareLaunchArgument(
            'dock_file', default_value='/ws/zones/dock.yaml',
            description='Path to persisted dock position YAML'
        ),
        DeclareLaunchArgument(
            'frame_id', default_value='map',
            description='ROS frame ID for all spatial operations'
        ),

        # ── Coverage Path Generator ───────────────────────────────────────
        Node(
            package='openmower_mission',
            executable='coverage_path_generator',
            name='coverage_path_generator',
            parameters=[
                config_file,
                {
                    'stripe_width_m': LaunchConfiguration('stripe_width_m'),
                    'overlap_m': LaunchConfiguration('overlap_m'),
                    'approach_angle_deg': LaunchConfiguration('approach_angle_deg'),
                    'frame_id': LaunchConfiguration('frame_id'),
                }
            ],
            output='screen',
            emulate_tty=True,
        ),

        # ── Mission Executor ──────────────────────────────────────────────
        Node(
            package='openmower_mission',
            executable='mission_executor',
            name='mission_executor',
            parameters=[config_file],
            output='screen',
            emulate_tty=True,
        ),

        # ── Dock Manager ──────────────────────────────────────────────────
        Node(
            package='openmower_mission',
            executable='dock_manager',
            name='dock_manager',
            parameters=[
                config_file,
                {'dock_file': LaunchConfiguration('dock_file')},
            ],
            output='screen',
            emulate_tty=True,
        ),

        # ── Zone Costmap Publisher ────────────────────────────────────────
        Node(
            package='openmower_mission',
            executable='zone_costmap_publisher',
            name='zone_costmap_publisher',
            parameters=[config_file],
            output='screen',
            emulate_tty=True,
        ),
    ])
