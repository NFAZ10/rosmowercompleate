#!/usr/bin/env python3

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PythonExpression
from launch.conditions import IfCondition
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    # Get package directory
    pkg_dir = get_package_share_directory('gps_rtk')
    
    # Declare launch arguments
    serial_port_arg = DeclareLaunchArgument(
        'serial_port',
        default_value='/dev/ttyTHS1',
        description='Serial port for GPS module (e.g., /dev/ttyAMA0 for GPIO UART)'
    )
    
    baud_rate_arg = DeclareLaunchArgument(
        'baud_rate',
        default_value='115200',
        description='Baud rate for GPS communication'
    )
    
    use_rtk_arg = DeclareLaunchArgument(
        'use_rtk',
        default_value='false',
        description='Enable RTK mode'
    )
    
    ntrip_profile_arg = DeclareLaunchArgument(
        'ntrip_profile',
        default_value='default',
        description='NTRIP server profile to use (default or alt)'
    )
    
    # Determine config file based on ntrip_profile
    # If ntrip_profile is 'alt', use gps_params_alt.yaml, otherwise use gps_params.yaml
    config_file_default = os.path.join(pkg_dir, 'config', 'gps_params.yaml')
    config_file_alt = os.path.join(pkg_dir, 'config', 'gps_params_alt.yaml')
    
    config_file_arg = DeclareLaunchArgument(
        'config_file',
        default_value=config_file_default,
        description='Path to GPS configuration file (overrides ntrip_profile if set)'
    )
    
    # GPS Node with default config
    gps_node_default = Node(
        package='gps_rtk',
        executable='gps_node',
        name='gps_node',
        output='screen',
        condition=IfCondition(
            PythonExpression(['"', LaunchConfiguration('ntrip_profile'), '" == "default"'])
        ),
        parameters=[
            config_file_default,
            {
                'serial_port': LaunchConfiguration('serial_port'),
                'baud_rate': LaunchConfiguration('baud_rate'),
                'use_rtk': LaunchConfiguration('use_rtk'),
            }
        ],
        remappings=[
            ('gps/fix', 'gps/fix'),
            ('gps/velocity', 'gps/velocity'),
        ]
    )
    
    # GPS Node with alternate config
    gps_node_alt = Node(
        package='gps_rtk',
        executable='gps_node',
        name='gps_node',
        output='screen',
        condition=IfCondition(
            PythonExpression(['"', LaunchConfiguration('ntrip_profile'), '" == "alt"'])
        ),
        parameters=[
            config_file_alt,
            {
                'serial_port': LaunchConfiguration('serial_port'),
                'baud_rate': LaunchConfiguration('baud_rate'),
                'use_rtk': LaunchConfiguration('use_rtk'),
            }
        ],
        remappings=[
            ('gps/fix', 'gps/fix'),
            ('gps/velocity', 'gps/velocity'),
        ]
    )
    
    return LaunchDescription([
        serial_port_arg,
        baud_rate_arg,
        use_rtk_arg,
        ntrip_profile_arg,
        config_file_arg,
        gps_node_default,
        gps_node_alt,
    ])
