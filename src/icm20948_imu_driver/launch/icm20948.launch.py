#!/usr/bin/env python3
"""
Launch file for ICM20948 IMU driver
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """Generate launch description for ICM20948 IMU driver"""
    
    # Declare launch arguments
    i2c_bus_arg = DeclareLaunchArgument(
        'i2c_bus',
        default_value='7',
        description='I2C bus number'
    )
    
    i2c_address_arg = DeclareLaunchArgument(
        'i2c_address',
        default_value='0x68',
        description='I2C address of ICM20948 (hex)'
    )
    
    frame_id_arg = DeclareLaunchArgument(
        'frame_id',
        default_value='imu_link',
        description='Frame ID for IMU messages'
    )
    
    publish_rate_arg = DeclareLaunchArgument(
        'publish_rate',
        default_value='100.0',
        description='Publishing rate in Hz'
    )
    
    # ICM20948 node
    icm20948_node = Node(
        package='icm20948_imu_driver',
        executable='icm20948_node',
        name='icm20948_imu',
        output='screen',
        parameters=[{
            'i2c_bus': LaunchConfiguration('i2c_bus'),
            'i2c_address': int(LaunchConfiguration('i2c_address'), 16) if isinstance(LaunchConfiguration('i2c_address'), str) else LaunchConfiguration('i2c_address'),
            'frame_id': LaunchConfiguration('frame_id'),
            'publish_rate': LaunchConfiguration('publish_rate'),
            'publish_temperature': True,
            'publish_magnetometer': True,
        }],
        remappings=[
            ('imu/data', 'imu/data_raw'),
        ]
    )
    
    return LaunchDescription([
        i2c_bus_arg,
        i2c_address_arg,
        frame_id_arg,
        publish_rate_arg,
        icm20948_node,
    ])
