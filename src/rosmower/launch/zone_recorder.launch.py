#!/usr/bin/env python3
"""
Zone Recorder Launch File
Launches the GPS-based zone recorder node for recording zone boundaries
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    """Generate launch description for zone recorder"""
    
    # Declare launch arguments
    waypoint_min_distance_arg = DeclareLaunchArgument(
        'waypoint_min_distance',
        default_value='0.5',
        description='Minimum distance between waypoints in meters'
    )
    
    simplification_tolerance_arg = DeclareLaunchArgument(
        'simplification_tolerance',
        default_value='0.3',
        description='Douglas-Peucker simplification tolerance in meters'
    )

    gps_accuracy_threshold_arg = DeclareLaunchArgument(
        'gps_accuracy_threshold',
        default_value='5.0',
        description='Minimum GPS accuracy to record waypoints (meters)'
    )
    
    visual_odometry_enabled_arg = DeclareLaunchArgument(
        'visual_odometry_enabled',
        default_value='false',
        description='Enable visual odometry fusion (for Isaac ROS stereo)'
    )
    
    frame_id_arg = DeclareLaunchArgument(
        'frame_id',
        default_value='map',
        description='Frame ID for zone polygons'
    )
    
    publish_rate_arg = DeclareLaunchArgument(
        'publish_rate',
        default_value='2.0',
        description='Status publishing rate in Hz'
    )
    
    gps_topic_arg = DeclareLaunchArgument(
        'gps_topic',
        default_value='/gps/fix',
        description='GPS fix topic to subscribe to'
    )
    
    visual_odom_topic_arg = DeclareLaunchArgument(
        'visual_odom_topic',
        default_value='/visual_odometry/pose',
        description='Visual odometry pose topic (for future Isaac ROS integration)'
    )
    
    # Zone Recorder Node
    zone_recorder_node = Node(
        package='rosmower',
        executable='zone_recorder.py',
        name='zone_recorder',
        output='screen',
        parameters=[{
            'waypoint_min_distance': LaunchConfiguration('waypoint_min_distance'),
            'simplification_tolerance': LaunchConfiguration('simplification_tolerance'),
            'gps_accuracy_threshold': LaunchConfiguration('gps_accuracy_threshold'),
            'visual_odometry_enabled': LaunchConfiguration('visual_odometry_enabled'),
            'frame_id': LaunchConfiguration('frame_id'),
            'publish_rate': LaunchConfiguration('publish_rate'),
            'gps_topic': LaunchConfiguration('gps_topic'),
            'visual_odom_topic': LaunchConfiguration('visual_odom_topic'),
        }]
    )
    
    return LaunchDescription([
        waypoint_min_distance_arg,
        simplification_tolerance_arg,
        gps_accuracy_threshold_arg,
        visual_odometry_enabled_arg,
        frame_id_arg,
        publish_rate_arg,
        gps_topic_arg,
        visual_odom_topic_arg,
        zone_recorder_node,
    ])
