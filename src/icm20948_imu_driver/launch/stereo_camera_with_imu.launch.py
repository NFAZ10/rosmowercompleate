#!/usr/bin/env python3
"""
Launch file for dual camera setup with IMU
Launches both stereo cameras and IMU sensor
"""

from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    """Generate launch description for stereo camera setup with IMU"""
    
    # Include stereo camera launch file
    stereo_camera_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('stereo_camera_setup'),
                'launch',
                'dual_imx219_stereo.launch.py'
            ])
        ])
    )
    
    # Include ICM20948 IMU launch file
    imu_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([
                FindPackageShare('icm20948_imu_driver'),
                'launch',
                'icm20948.launch.py'
            ])
        ]),
        launch_arguments={
            'i2c_bus': '1',
            'i2c_address': '0x68',
            'frame_id': 'imu_link',
            'publish_rate': '100.0',
        }.items()
    )
    
    return LaunchDescription([
        stereo_camera_launch,
        imu_launch,
    ])
