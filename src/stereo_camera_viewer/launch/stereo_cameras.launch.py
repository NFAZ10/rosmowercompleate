#!/usr/bin/env python3

"""
Stereo Camera Launch for Jetson CSI Cameras (IMX219)
Publishes to ROS 2 topics for RViz and Isaac ROS navigation
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    # Get package directory
    pkg_dir = get_package_share_directory('stereo_camera_viewer')
    
    # Declare launch arguments with sensible defaults for Jetson + IMX219
    left_camera_arg = DeclareLaunchArgument(
        'left_camera_id',
        default_value='0',
        description='Left camera CSI sensor ID (0 for CAM0 port)'
    )
    
    right_camera_arg = DeclareLaunchArgument(
        'right_camera_id',
        default_value='1',
        description='Right camera CSI sensor ID (1 for CAM1 port)'
    )
    
    width_arg = DeclareLaunchArgument(
        'width',
        default_value='1280',
        description='Camera width (1280 recommended for IMX219 @ 720p)'
    )
    
    height_arg = DeclareLaunchArgument(
        'height',
        default_value='720',
        description='Camera height (720 recommended for good performance)'
    )
    
    fps_arg = DeclareLaunchArgument(
        'fps',
        default_value='30',
        description='Frame rate (30 fps recommended)'
    )
    
    use_gstreamer_arg = DeclareLaunchArgument(
        'use_gstreamer',
        default_value='false',
        description='Use GStreamer for CSI cameras (false=V4L2, works better in Docker)'
    )
    
    flip_method_arg = DeclareLaunchArgument(
        'flip_method',
        default_value='0',
        description='Image rotation: 0=none, 2=rotate-180, 4=horizontal-flip, 6=vertical-flip'
    )
    
    frame_id_arg = DeclareLaunchArgument(
        'frame_id',
        default_value='stereo_camera',
        description='TF frame ID for camera'
    )
    
    # Stereo Camera Node
    stereo_camera_node = Node(
        package='stereo_camera_viewer',
        executable='stereo_camera_node',
        name='stereo_camera_node',
        output='screen',
        parameters=[{
            'left_camera_id': LaunchConfiguration('left_camera_id'),
            'right_camera_id': LaunchConfiguration('right_camera_id'),
            'width': LaunchConfiguration('width'),
            'height': LaunchConfiguration('height'),
            'fps': LaunchConfiguration('fps'),
            'use_gstreamer': LaunchConfiguration('use_gstreamer'),
            'flip_method': LaunchConfiguration('flip_method'),
            'frame_id': LaunchConfiguration('frame_id'),
        }],
        emulate_tty=True
    )
    
    return LaunchDescription([
        left_camera_arg,
        right_camera_arg,
        width_arg,
        height_arg,
        fps_arg,
        use_gstreamer_arg,
        flip_method_arg,
        frame_id_arg,
        stereo_camera_node,
    ])
