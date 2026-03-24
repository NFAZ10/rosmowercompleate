#!/usr/bin/env python3
"""
Launch file for MQTT Bridge
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import EnvironmentVariable, LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    # Get package directory
    pkg_dir = get_package_share_directory('mqtt_bridge')
    config_file = os.path.join(pkg_dir, 'config', 'mqtt_params.yaml')
    
    # Declare launch arguments
    mqtt_broker_arg = DeclareLaunchArgument(
        'mqtt_broker',
        default_value=EnvironmentVariable(
            'ROSMOWER_MQTT_BROKER',
            default_value='homeassistant.local'
        ),
        description='MQTT broker address'
    )
    
    mqtt_port_arg = DeclareLaunchArgument(
        'mqtt_port',
        default_value='1883',
        description='MQTT broker port'
    )

    mqtt_username_arg = DeclareLaunchArgument(
        'mqtt_username',
        default_value=EnvironmentVariable(
            'ROSMOWER_MQTT_USERNAME',
            default_value=''
        ),
        description='MQTT username'
    )

    mqtt_password_arg = DeclareLaunchArgument(
        'mqtt_password',
        default_value=EnvironmentVariable(
            'ROSMOWER_MQTT_PASSWORD',
            default_value=''
        ),
        description='MQTT password'
    )

    mqtt_client_id_arg = DeclareLaunchArgument(
        'mqtt_client_id',
        default_value=EnvironmentVariable(
            'ROSMOWER_MQTT_CLIENT_ID',
            default_value='rosmower_mqtt_bridge'
        ),
        description='MQTT client identifier'
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
                'mqtt_username': LaunchConfiguration('mqtt_username'),
                'mqtt_password': LaunchConfiguration('mqtt_password'),
                'mqtt_client_id': LaunchConfiguration('mqtt_client_id'),
                'base_topic': LaunchConfiguration('base_topic'),
            }
        ],
        respawn=True,
        respawn_delay=2.0
    )
    
    return LaunchDescription([
        mqtt_broker_arg,
        mqtt_port_arg,
        mqtt_username_arg,
        mqtt_password_arg,
        mqtt_client_id_arg,
        base_topic_arg,
        mqtt_bridge_node
    ])
