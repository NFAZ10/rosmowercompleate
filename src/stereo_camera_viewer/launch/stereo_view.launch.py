#!/usr/bin/env python3

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    # Get package directory
    pkg_dir = get_package_share_directory('stereo_camera_viewer')
    
    # Declare launch arguments
    left_camera_arg = DeclareLaunchArgument(
        'left_camera_id',
        default_value='0',
        description='Left camera ID (CSI camera ID or /dev/video* index)'
    )
    
    right_camera_arg = DeclareLaunchArgument(
        'right_camera_id',
        default_value='1',
        description='Right camera ID (CSI camera ID or /dev/video* index)'
    )
    
    width_arg = DeclareLaunchArgument(
        'width',
        default_value='1280',
        description='Camera width'
    )
    
    height_arg = DeclareLaunchArgument(
        'height',
        default_value='720',
        description='Camera height'
    )
    
    fps_arg = DeclareLaunchArgument(
        'fps',
        default_value='30',
        description='Frame rate'
    )
    
    use_gstreamer_arg = DeclareLaunchArgument(
        'use_gstreamer',
        default_value='true',
        description='Use GStreamer for CSI cameras (true for Jetson CSI, false for USB)'
    )
    
    show_viewer_arg = DeclareLaunchArgument(
        'show_viewer',
        default_value='true',
        description='Launch the OpenCV viewer'
    )
    
    config_file_arg = DeclareLaunchArgument(
        'config_file',
        default_value=os.path.join(pkg_dir, 'config', 'stereo_params.yaml'),
        description='Path to camera configuration file'
    )
    
    # Stereo Camera Node
    stereo_camera_node = Node(
        package='stereo_camera_viewer',
        executable='stereo_camera_node',
        name='stereo_camera_node',
        output='screen',
        parameters=[
            LaunchConfiguration('config_file'),
            {
                'left_camera_id': LaunchConfiguration('left_camera_id'),
                'right_camera_id': LaunchConfiguration('right_camera_id'),
                'width': LaunchConfiguration('width'),
                'height': LaunchConfiguration('height'),
                'fps': LaunchConfiguration('fps'),
                'use_gstreamer': LaunchConfiguration('use_gstreamer'),
            }
        ]
    )
    
    # Simple Viewer Node (conditionally launched)
    simple_viewer_node = Node(
        package='stereo_camera_viewer',
        executable='simple_viewer',
        name='simple_viewer',
        output='screen',
        parameters=[LaunchConfiguration('config_file')],
        condition=IfCondition(LaunchConfiguration('show_viewer'))
    )
    
    return LaunchDescription([
        left_camera_arg,
        right_camera_arg,
        width_arg,
        height_arg,
        fps_arg,
        use_gstreamer_arg,
        show_viewer_arg,
        config_file_arg,
        stereo_camera_node,
        simple_viewer_node,
    ])
