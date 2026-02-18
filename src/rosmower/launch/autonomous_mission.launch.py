#!/usr/bin/env python3
"""
Autonomous Mission Launch File
Launches battery monitor and zone manager nodes for autonomous operation
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    # Get package directory
    pkg_dir = get_package_share_directory('rosmower')
    
    # Declare launch arguments
    zones_directory = LaunchConfiguration('zones_directory')
    zones_directory_arg = DeclareLaunchArgument(
        'zones_directory',
        default_value='/ws/zones',
        description='Directory containing zone definition files'
    )
    
    # Battery Monitor Node
    battery_monitor_node = Node(
        package='rosmower',
        executable='battery_monitor.py',
        name='battery_monitor',
        output='screen',
        parameters=[{
            'low_battery_threshold': 25.0,
            'critical_battery_threshold': 15.0,
            'charged_threshold': 95.0,
            'charging_current_threshold': -0.1
        }],
        remappings=[
            # Remap to actual battery topics
            ('/percent', '/battery/percentage'),
            ('/current', '/battery/current'),
        ]
    )
    
    # Zone Manager Node
    zone_manager_node = Node(
        package='rosmower',
        executable='zone_manager.py',
        name='zone_manager',
        output='screen',
        parameters=[{
            'zones_directory': zones_directory,
            'publish_rate': 1.0,
            'frame_id': 'map'
        }]
    )
    
    return LaunchDescription([
        zones_directory_arg,
        battery_monitor_node,
        zone_manager_node,
    ])
