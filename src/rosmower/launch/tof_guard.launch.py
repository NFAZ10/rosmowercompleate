from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    # Launch arguments
    min_distance_arg = DeclareLaunchArgument(
        'min_distance_mm',
        default_value='200',
        description='Default minimum safe distance in millimeters for all channels'
    )
    
    min_distances_ch0_arg = DeclareLaunchArgument(
        'min_distance_ch0',
        default_value='200',
        description='Minimum safe distance for channel 0 (left sensor) in millimeters'
    )
    
    min_distances_ch1_arg = DeclareLaunchArgument(
        'min_distance_ch1', 
        default_value='200',
        description='Minimum safe distance for channel 1 (right sensor) in millimeters'
    )
    
    min_distances_ch2_arg = DeclareLaunchArgument(
        'min_distance_ch2',
        default_value='200', 
        description='Minimum safe distance for channel 2 (front sensor) in millimeters'
    )
    
    cmd_vel_in_arg = DeclareLaunchArgument(
        'cmd_vel_in',
        default_value='/cmd_vel_in',
        description='Input velocity command topic'
    )
    
    cmd_vel_out_arg = DeclareLaunchArgument(
        'cmd_vel_out', 
        default_value='/cmd_vel',
        description='Output velocity command topic'
    )

    return LaunchDescription([
        min_distance_arg,
        min_distances_ch0_arg,
        min_distances_ch1_arg,
        min_distances_ch2_arg,
        cmd_vel_in_arg,
        cmd_vel_out_arg,
        
        # ToF Guard node - monitors VL53 sensors and blocks cmd_vel when obstacles detected
        Node(
            package='rosmower',
            executable='tof_guard.py',
            name='tof_guard',
            output='screen',
            parameters=[{
                'min_distance_mm': LaunchConfiguration('min_distance_mm'),
                'min_distances_by_channel': [
                    LaunchConfiguration('min_distance_ch0'),
                    LaunchConfiguration('min_distance_ch1'), 
                    LaunchConfiguration('min_distance_ch2')
                ],
                'cmd_vel_in': LaunchConfiguration('cmd_vel_in'),
                'cmd_vel_out': LaunchConfiguration('cmd_vel_out'),
                'cooldown_s': 0.5,
            }]
        ),
    ])
