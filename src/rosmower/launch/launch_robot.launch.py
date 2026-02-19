# rosmower/launch/main.launch.py

import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
    GroupAction,
    TimerAction,
    SetEnvironmentVariable,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch.conditions import IfCondition, UnlessCondition

# Full device path for hoverboard Arduino
BY_ID = '/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0'

# RPLIDAR C1 device path (CP2102N chip)
RPLIDAR_BY_ID = "/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0"

# Default FCU path for MAVROS (override at launch with: `ros2 launch ... dev:=/dev/ttyACM0`)
DEFAULT_FCU = '/dev/serial/by-id/usb-ArduPilot_SpeedyBeeF405WING_310037000850314E41313720-if00'


def generate_launch_description():
    # --- Launch arguments (must be declared before use in node conditions) ---
    use_vesc            = LaunchConfiguration('use_vesc')
    use_stereo_camera  = LaunchConfiguration('use_stereo_camera')

    # --- Battery Splitter Node ---
    battery_splitter_node = Node(
        package='rosmower',
        executable='battery_splitter.py',
        name='battery_splitter',
        output='screen',
        parameters=[{
            'source_topic': '/mavros/battery',
            'voltage_topic': '/voltage',
            'percent_topic': '/percent',
            'current_topic': '/current',
            'percent_scale_0_100': True
        }]
    )
    # --- Stereo CSI Cameras (IMX219) ---
    stereo_camera_node = Node(
        package='stereo_camera_viewer',
        executable='stereo_camera_node',
        name='stereo_camera_node',
        output='screen',
        parameters=[{
            'left_camera_id': 2,       # /dev/video2 = left IMX219 CSI camera (V4L2 fallback)
            'right_camera_id': 1,      # /dev/video1 = right IMX219 CSI camera (V4L2 fallback)
            'left_sensor_id': 0,       # nvarguscamerasrc sensor-id for left (CAM0 port)
            'right_sensor_id': 1,      # nvarguscamerasrc sensor-id for right (CAM1 port)
            'width': 1280,             # Native supported resolution
            'height': 720,             # Use 1280x720 @ 30fps
            'fps': 15,
            'use_gstreamer': True,     # nvarguscamerasrc via Jetson ISP (EGL_PLATFORM=surfaceless required)
            'flip_method': 0,          # 0=none, 2=rotate-180
            'left_frame_id': 'left_camera_link',   # Match URDF
            'right_frame_id': 'right_camera_link', # Match URDF
            'jpeg_quality': 60,        # 50=minimal, 60=balanced, 75=high quality
            'publish_raw': False       # KEEP FALSE to prevent crashes (compressed only)
        }],
        emulate_tty=True,
        condition=IfCondition(use_stereo_camera)  # Enable/disable via launch arg
    )
    pkg = get_package_share_directory('rosmower')

    # --- Launch arguments ---
    use_sim_time       = LaunchConfiguration('use_sim_time')
    use_ros2_control   = LaunchConfiguration('use_ros2_control')
    use_rosbridge      = LaunchConfiguration('use_rosbridge')
    use_twist_mux      = LaunchConfiguration('use_twist_mux')
    use_mavros         = LaunchConfiguration('use_mavros')
    dev                = LaunchConfiguration('dev')  # MAVROS serial device
    arm                = LaunchConfiguration('arm')  # Explicit flag to arm motors
    use_joint_state_gui = LaunchConfiguration('use_joint_state_gui')  # Toggle GUI sliders

    # Build MAVROS fcu_url = serial://<dev>:115200
    fcu_url = ['serial://', dev, ':115200']

    # --- Global: keep console quiet ---
    quiet_env = SetEnvironmentVariable('RCUTILS_LOGGING_SEVERITY_THRESHOLD', 'WARN')

    # --- Core robot state publisher ---
    rsp = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg, 'launch', 'rsp.launch.py')),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'use_ros2_control': use_ros2_control,
        }.items(),
    )

    # --- Joint State Publisher (only when NOT using ros2_control) ---

    # Headless publisher:
    jsp = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        output='log',
        arguments=['--ros-args', '--log-level', 'warn'],
        condition=UnlessCondition(use_joint_state_gui)
    )
    # Run either GUI or headless, but only if ros2_control is disabled
    jsp_group = GroupAction(
        actions=[jsp],
        condition=UnlessCondition(use_ros2_control)
    )

    # --- Optional: Twist Mux support ---
    twist_mux_params = os.path.join(pkg, 'config', 'twist_mux.yaml')
    twist_mux_ctrl = Node(
        package='twist_mux',
        executable='twist_mux',
        output='log',
        arguments=['--ros-args', '--log-level', 'warn'],
        parameters=[twist_mux_params],
        remappings=[('/cmd_vel_out', '/diff_cont/cmd_vel_unstamped')],
    )
    twist_mux_bridge = Node(
        package='twist_mux',
        executable='twist_mux',
        output='log',
        arguments=['--ros-args', '--log-level', 'warn'],
        parameters=[twist_mux_params],
        remappings=[('/cmd_vel_out', '/cmd_vel')],
    )
    twist_mux_to_controller = GroupAction(actions=[twist_mux_ctrl], condition=IfCondition(use_ros2_control))
    twist_mux_to_bridge = GroupAction(actions=[twist_mux_bridge], condition=IfCondition(use_twist_mux))

    # --- Hoverboard bridge (only starts if --arm flag is passed) ---
    hoverboard = Node(
        package='rosmower',
        executable='hoverboard_bridge_node.py',
        name='hoverboard_bridge',
        output='log',
        arguments=['--ros-args', '--log-level', 'warn'],
        parameters=[{
            'port': BY_ID,
            'baud': 115200,
            'max_pwm': 100,
            'max_lin': 1.0,
            'max_ang': 2.0,
            'stat_period': 0.5,
            'arm_on_start': True,
            'wheel_radius': 0.4364,
            'wheel_separation': 0.52,
        }],
        condition=IfCondition(arm)
    )
    hoverboard_group = GroupAction(actions=[hoverboard], condition=UnlessCondition(use_ros2_control))

    # --- ICM20948 IMU Driver ---
    icm20948_pkg = get_package_share_directory('icm20948_imu_driver')
    icm20948_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(icm20948_pkg, 'launch', 'icm20948.launch.py')),
        launch_arguments={
            'i2c_bus': '7',
            'i2c_address': '0x68',
            'frame_id': 'imu_link',
            'publish_rate': '100.0',
        }.items(),
    )

    # --- IMU Bridge Node ---
    imu_bridge =  Node(
        package='rosmower',
        executable='imu_bridge.py',
        name='imu_bridge',
        output='log',
        arguments=['--ros-args', '--log-level', 'warn'],
        parameters=[{
            'mavros_imu_topic': '/mavros/imu/data',
            'output_imu_topic': '/imu/data_raw'
        }]
    )

    # --- EKF Node (robot_localization) ---
    ekf_config = os.path.join(pkg, 'config', 'ekf.yaml')
    ekf_node = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='log',
        arguments=['--ros-args', '--log-level', 'warn'],
        parameters=[ekf_config],
        remappings=[('/odometry/filtered', '/odom')],
    )

    # --- Mode Manager Node ---
    mode_manager_node = Node(
        package='rosmower',
        executable='mode_manager.py',
        name='mode_manager',
        output='screen',
        parameters=[{
            'initial_mode': 'full'
        }]
    )
    
    # --- Optional: rosbridge websocket ---
    rosbridge_node = Node(
        package='rosbridge_server',
        executable='rosbridge_websocket',
        name='rosbridge_websocket',
        output='log',
        arguments=['--ros-args', '--log-level', 'warn'],
        parameters=[{'port': 9090}],
        condition=IfCondition(use_rosbridge),
    )

    # --- RPLIDAR motor control node ---
    rplidar_motor_control = Node(
        package='rosmower',
        executable='rplidar_motor_control.py',
        name='rplidar_motor_control',
        output='log',
        arguments=['--ros-args', '--log-level', 'warn'],
        parameters=[{
            'topic_name': '/scan',
            'node1': 'rviz',
            'node2': 'move_base',
            'seconds_between_tries': 5,
        }],
    )

    # --- RPLIDAR C1 driver node ---
    rplidar_node = Node(
        package='sllidar_ros2',
        executable='sllidar_node',
        name='rplidar',
        output='log',
        arguments=['--ros-args', '--log-level', 'info'],
        parameters=[{
                'serial_port': RPLIDAR_BY_ID,
                'serial_baudrate': 460800,  # C1 uses 460800 baud rate
                'frame_id': 'lidar_link',    # Match URDF frame
                'angle_compensate': True,
                'scan_mode': 'Standard',     # C1 supports Standard mode
                'inverted': False,
        }],
    )


    relay = Node(
        package='rosmower',              # replace with your package
        executable='relay_control_node.py',
        name='relay_control',
        output='screen',
        parameters=[{
            'chip': 'gpiochip0',
            'line': 17,
            'active_high': True,
            'relay_on_start': False
        }]
    )

    tof = Node(
    package='rosmower',      # replace with your package
    executable='tof_to_scan.py',# matches entry point or script name
    name='tof_to_scan',
    output='screen'
)





    

    # --- VESC Differential Drive Motor Controller ---
    vesc_pkg = get_package_share_directory('vesc_driver')
    vesc_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(vesc_pkg, 'launch', 'vesc_driver.launch.py')),
        condition=IfCondition(use_vesc),
    )

    # --- MAVROS Node ---
    mavros_node = Node(
        package='mavros',
        executable='mavros_node',
       #output='screen',
        parameters=[{
            'fcu_url': fcu_url,
            'fcu_protocol': 'v2.0',
        }],
        condition=IfCondition(use_mavros),
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        DeclareLaunchArgument('use_ros2_control', default_value='false'),
        DeclareLaunchArgument('use_twist_mux', default_value='false'),
        DeclareLaunchArgument('use_mavros', default_value='true'),
        DeclareLaunchArgument('use_stereo_camera', default_value='true',
                              description='Enable stereo cameras (disable if causing crashes)'),

        DeclareLaunchArgument('use_joint_state_gui', default_value='false',
                              description='Use joint_state_publisher_gui sliders'),
        DeclareLaunchArgument('dev', default_value=DEFAULT_FCU),
        DeclareLaunchArgument('arm', default_value='true', description='Enable motor arming if true'),
        DeclareLaunchArgument('use_vesc', default_value='true',
                              description='Launch VESC differential drive motor controller'),

        quiet_env,
        rsp,
        mode_manager_node,    # Mode manager for runtime mode switching
        jsp_group,            # <-- NEW: joint state publisher (headless or GUI)
        icm20948_launch,      # ICM20948 IMU driver
        imu_bridge,
        rplidar_node,           # RPlidar C1 with motor control - ENABLED
        stereo_camera_node,        # Stereo CSI cameras (IMX219) - Now with HW accel
        battery_splitter_node,
        mavros_node,
        vesc_launch,          # VESC differential drive motor controller

        
    ])

