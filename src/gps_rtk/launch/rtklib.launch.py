#!/usr/bin/env python3
"""
ROS2 Launch file for RTK GPS using RTKLIB rtkrcv
Starts RTKLIB rtkrcv and reads NMEA from TCP port 9001
Requires: sudo apt install ros-humble-nmea-navsat-driver
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare
from launch.conditions import IfCondition

def generate_launch_description():
    
    # Get package directory
    pkg_share = FindPackageShare('gps_rtk')
    
    # RTKLIB binary and config paths
    rtkrcv_bin = PathJoinSubstitution([pkg_share, 'rtklib', 'rtkrcv'])
    rover_config = PathJoinSubstitution([pkg_share, 'config', 'rover.conf'])
    
    # Declare launch arguments
    rtklib_ip_arg = DeclareLaunchArgument(
        'rtklib_ip',
        default_value='127.0.0.1',
        description='IP address of RTKLIB rtkrcv TCP server'
    )
    
    rtklib_port_arg = DeclareLaunchArgument(
        'rtklib_port',
        default_value='9001',
        description='TCP port of RTKLIB rtkrcv output'
    )
    
    frame_id_arg = DeclareLaunchArgument(
        'frame_id',
        default_value='gps',
        description='Frame ID for GPS messages'
    )
    
    start_rtklib_arg = DeclareLaunchArgument(
        'start_rtklib',
        default_value='true',
        description='Start RTKLIB rtkrcv automatically'
    )
    
    # Start RTKLIB rtkrcv process
    # Note: Runs with -s flag to auto-start on launch
    rtklib_process = ExecuteProcess(
        condition=IfCondition(LaunchConfiguration('start_rtklib')),
        cmd=[rtkrcv_bin, '-s', '-o', rover_config],
        name='rtkrcv',
        output='screen',
        shell=False,
    )
    
    # NMEA socket driver node - reads from RTKLIB TCP output
    nmea_driver = Node(
        package='nmea_navsat_driver',
        executable='nmea_socket_driver',
        name='rtklib_gps',
        output='screen',
        parameters=[{
            'ip': LaunchConfiguration('rtklib_ip'),
            'port': LaunchConfiguration('rtklib_port'),
            'frame_id': LaunchConfiguration('frame_id'),
            'time_ref_source': LaunchConfiguration('frame_id'),
            'useRMC': True,
            'use_GNSS_time': False,
            'valid_fix_status': [1, 2, 4, 5],  # Accept RTK fixes
        }],
        remappings=[
            ('fix', '/gps/fix'),
            ('vel', '/gps/vel'),
            ('time_reference', '/gps/time'),
        ]
    )
    
    return LaunchDescription([
        rtklib_ip_arg,
        rtklib_port_arg,
        frame_id_arg,
        start_rtklib_arg,
        rtklib_process,
        nmea_driver,
    ])
