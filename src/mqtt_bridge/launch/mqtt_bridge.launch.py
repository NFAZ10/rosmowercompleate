#!/usr/bin/env python3
"""
Launch file for MQTT Bridge
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    # Get package directory
    pkg_dir = get_package_share_directory('mqtt_bridge')
    config_file = os.path.join(pkg_dir, 'config', 'mqtt_params.yaml')
    
    # Declare launch arguments
    mqtt_broker_arg = DeclareLaunchArgument(
        'mqtt_broker',
        default_value='localhost',
        description='MQTT broker address'
    )
    
    mqtt_port_arg = DeclareLaunchArgument(
        'mqtt_port',
        default_value='1883',
        description='MQTT broker port'
    )
    
    base_topic_arg = DeclareLaunchArgument(
        'base_topic',
        default_value='rosmower',
        description='Base MQTT topic prefix'
    )
    
    # MQTT Bridge Node
    mqtt_bridge_node = Node(
        package='mqtt_bridge',
        executable='mqtt_bridge_node',
        name='mqtt_bridge',
        output='screen',
        parameters=[
            config_file,
            {
                'mqtt_broker': LaunchConfiguration('mqtt_broker'),
                'mqtt_port': LaunchConfiguration('mqtt_port'),
                'base_topic': LaunchConfiguration('base_topic'),
            }
        ],
        respawn=True,
        respawn_delay=2.0
    )
    
    return LaunchDescription([
        mqtt_broker_arg,
        mqtt_port_arg,
        base_topic_arg,
        mqtt_bridge_node
    ])
