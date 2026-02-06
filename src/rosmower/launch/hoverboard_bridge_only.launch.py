from launch import LaunchDescription
from launch_ros.actions import Node

BY_ID = '/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0'

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='rosmower',
            executable='hoverboard_bridge_node.py',
            name='hoverboard_bridge',
            output='screen',
            parameters=[{
                 'port': BY_ID,
                 'baud': 115200,
                 'max_pwm': 50,
                 'max_lin': 3.0,
                 'max_ang': 0.1,
                 'stat_period': 0.5,
                 'arm_on_start': True,
                 'wheel_radius': 0.4364,
                 'wheel_separation': 0.52,
            }]
        )
    ])
