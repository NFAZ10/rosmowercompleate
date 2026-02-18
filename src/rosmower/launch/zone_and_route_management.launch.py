#!/usr/bin/env python3
"""
Launch file for multi-zone and route management system.

Launches:
- Zone Manager (enhanced with graph generation)
- Route Manager (route recording and storage)
- Route Planner (Dijkstra path planning)
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    # Declare launch arguments
    zones_directory_arg = DeclareLaunchArgument(
        'zones_directory',
        default_value='/ws/zones',
        description='Directory for zone storage'
    )
    
    routes_directory_arg = DeclareLaunchArgument(
        'routes_directory',
        default_value='/ws/routes',
        description='Directory for route storage'
    )
    
    frame_id_arg = DeclareLaunchArgument(
        'frame_id',
        default_value='map',
        description='Reference frame for zones and routes'
    )
    
    min_gps_quality_arg = DeclareLaunchArgument(
        'min_gps_quality_hdop',
        default_value='2.0',
        description='Minimum GPS quality (HDOP) for waypoint recording'
    )
    
    waypoint_spacing_arg = DeclareLaunchArgument(
        'waypoint_spacing_meters',
        default_value='1.0',
        description='Minimum distance between waypoints in meters'
    )
    
    # Zone Manager Node (enhanced with graph capabilities)
    zone_manager = Node(
        package='rosmower',
        executable='zone_manager.py',
        name='zone_manager',
        output='screen',
        parameters=[{
            'zones_directory': LaunchConfiguration('zones_directory'),
            'routes_directory': LaunchConfiguration('routes_directory'),
            'publish_rate': 1.0,
            'frame_id': LaunchConfiguration('frame_id'),
        }],
        remappings=[
            ('/zones', '/zones'),
            ('/zone/current', '/zone/current'),
            ('/zones/graph', '/zones/graph'),
        ]
    )
    
    # Route Manager Node (route recording)
    route_manager = Node(
        package='rosmower',
        executable='route_manager.py',
        name='route_manager',
        output='screen',
        parameters=[{
            'routes_directory': LaunchConfiguration('routes_directory'),
            'min_gps_quality_hdop': LaunchConfiguration('min_gps_quality_hdop'),
            'waypoint_spacing_meters': LaunchConfiguration('waypoint_spacing_meters'),
            'max_recording_time_seconds': 600,
            'publish_rate': 1.0,
            'frame_id': LaunchConfiguration('frame_id'),
        }],
        remappings=[
            ('/gps/fix', '/gps/fix'),
            ('/route/recording/status', '/route/recording/status'),
            ('/route/recording/path', '/route/recording/path'),
            ('/routes/all', '/routes/all'),
            ('/route/active', '/route/active'),
        ]
    )
    
    # Route Planner Node (Dijkstra algorithm)
    route_planner = Node(
        package='rosmower',
        executable='route_planner.py',
        name='route_planner',
        output='screen',
        parameters=[{
            'publish_rate': 1.0,
        }],
        remappings=[
            ('/zones/graph', '/zones/graph'),
            ('/routes/all', '/routes/all'),
        ]
    )
    
    return LaunchDescription([
        zones_directory_arg,
        routes_directory_arg,
        frame_id_arg,
        min_gps_quality_arg,
        waypoint_spacing_arg,
        zone_manager,
        route_manager,
        route_planner,
    ])
