#!/usr/bin/env python3

"""
Launch file for VESC differential drive controller
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    # Get package directory
    pkg_dir = get_package_share_directory('vesc_driver')
    
    # Declare launch arguments
    serial_port_arg = DeclareLaunchArgument(
        'serial_port',
        default_value='/dev/serial/by-id/usb-STMicroelectronics_ChibiOS_RT_Virtual_COM_Port_304-if00',
        description='Serial port for VESC connection (USB to VESC ID 0)'
    )
    
    baudrate_arg = DeclareLaunchArgument(
        'baudrate',
        default_value='115200',
        description='Serial baudrate'
    )
    
    wheel_radius_arg = DeclareLaunchArgument(
        'wheel_radius',
        default_value='0.1091',
        description='Wheel radius in meters (hoverboard wheel ~87.5mm)'
    )
    
    wheel_separation_arg = DeclareLaunchArgument(
        'wheel_separation',
        default_value='0.52',
        description='Wheel separation in meters'
    )
    
    
    left_can_id_arg = DeclareLaunchArgument(
        'left_vesc_can_id',
        default_value='0',
        description='Left VESC CAN ID (0 = USB connected)'
    )
    
    right_can_id_arg = DeclareLaunchArgument(
        'right_vesc_can_id',
        default_value='5',
        description='Right VESC CAN ID (connected via CAN bus)'
    )
    
    max_rpm_arg = DeclareLaunchArgument(
        'max_rpm',
        default_value='2500',
        description='Maximum ERPM (kept for reference; not used in duty cycle mode)'
    )

    max_lin_arg = DeclareLaunchArgument(
        'max_lin',
        default_value='1.0',
        description='Linear velocity (m/s) that maps to 100% duty cycle'
    )
    
    pole_pairs_arg = DeclareLaunchArgument(
        'pole_pairs',
        default_value='15',
        description='Motor pole pairs (hoverboard motors typically 15)'
    )
    
    invert_left_arg = DeclareLaunchArgument(
        'invert_left_motor',
        default_value='false',
        description='Invert left motor direction'
    )
    
    invert_right_arg = DeclareLaunchArgument(
        'invert_right_motor',
        default_value='false',
        description='Invert right motor direction'
    )
    
    control_rate_arg = DeclareLaunchArgument(
        'control_rate',
        default_value='50.0',
        description='Control loop rate in Hz'
    )
    
    telemetry_rate_arg = DeclareLaunchArgument(
        'telemetry_rate',
        default_value='10.0',
        description='Telemetry request rate in Hz'
    )
    
    publish_odom_arg = DeclareLaunchArgument(
        'publish_odom',
        default_value='true',
        description='Publish odometry from wheel encoders'
    )

    # VESC Driver Node
    #config_file = os.path.join(pkg_dir, 'config', 'vesc_driver.yaml')

    vesc_driver_node = Node(
        package='vesc_driver',
        executable='vesc_driver_node',
        name='vesc_driver',
        output='screen',
        remappings=[
            ('/cmd_vel', '/cmd_vel_motors'),  # gate node controls access
        ],
        parameters=[
            #config_file,
            {
            'serial_port': LaunchConfiguration('serial_port'),
            'baudrate': LaunchConfiguration('baudrate'),
            'wheel_radius': LaunchConfiguration('wheel_radius'),
            'wheel_separation': LaunchConfiguration('wheel_separation'),
            'left_vesc_can_id': LaunchConfiguration('left_vesc_can_id'),
            'right_vesc_can_id': LaunchConfiguration('right_vesc_can_id'),
            'max_rpm': LaunchConfiguration('max_rpm'),
            'max_lin': LaunchConfiguration('max_lin'),
            'pole_pairs': LaunchConfiguration('pole_pairs'),
            'invert_left_motor': LaunchConfiguration('invert_left_motor'),
            'invert_right_motor': LaunchConfiguration('invert_right_motor'),
            'control_rate': LaunchConfiguration('control_rate'),
            'telemetry_rate': LaunchConfiguration('telemetry_rate'),
            'publish_odom': LaunchConfiguration('publish_odom'),
            'odom_frame_id': 'odom',
            'base_frame_id': 'base_link',
        }],  # inline params override YAML values
        emulate_tty=True
    )
    
    return LaunchDescription([
        serial_port_arg,
        baudrate_arg,
        wheel_radius_arg,
        wheel_separation_arg,
        left_can_id_arg,
        right_can_id_arg,
        max_rpm_arg,
        max_lin_arg,
        pole_pairs_arg,
        invert_left_arg,
        invert_right_arg,
        control_rate_arg,
        telemetry_rate_arg,
        publish_odom_arg,
        vesc_driver_node,
    ])
