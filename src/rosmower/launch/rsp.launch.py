import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
import xacro

def generate_launch_description():
    # Launch arguments
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_ros2_control = LaunchConfiguration('use_ros2_control')
    
    pkg_path = get_package_share_directory('rosmower')
    xacro_file = os.path.join(pkg_path, 'description', 'rosmower.urdf.xacro')
    robot_description_config = xacro.process_file(xacro_file)

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_description_config.toxml(),
            'use_sim_time': use_sim_time
        }]
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false',
                            description='Use simulation time'),
        DeclareLaunchArgument('use_ros2_control', default_value='false',
                            description='Enable ros2_control (reserved for future use)'),
        robot_state_publisher
    ])