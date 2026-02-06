#!/usr/bin/env python3
"""
Mode Manager Node - Controls robot operational modes
Modes: idle, charging, mowing, full
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool


class ModeManager(Node):
    def __init__(self):
        super().__init__('mode_manager')
        
        # Declare parameter for initial mode
        self.declare_parameter('initial_mode', 'idle')
        
        # Current mode
        self.current_mode = self.get_parameter('initial_mode').get_parameter_value().string_value
        
        # Subscribe to mode change requests
        self.mode_sub = self.create_subscription(
            String,
            '/robot_mode_cmd',
            self.mode_callback,
            10
        )
        
        # Publish current mode
        self.mode_pub = self.create_publisher(String, '/robot_mode', 10)
        
        # Publishers for subsystem enable/disable
        self.motors_enable_pub = self.create_publisher(Bool, '/enable_motors', 10)
        self.sensors_enable_pub = self.create_publisher(Bool, '/enable_sensors', 10)
        self.gps_enable_pub = self.create_publisher(Bool, '/enable_gps', 10)
        self.lidar_enable_pub = self.create_publisher(Bool, '/enable_lidar', 10)
        self.camera_enable_pub = self.create_publisher(Bool, '/enable_camera', 10)
        
        # Publish mode status periodically
        self.timer = self.create_timer(1.0, self.publish_status)
        
        # Set initial mode
        self.set_mode(self.current_mode)
        
        self.get_logger().info(f'Mode Manager started in {self.current_mode} mode')
    
    def mode_callback(self, msg):
        """Handle mode change requests"""
        requested_mode = msg.data.lower()
        
        if requested_mode in ['idle', 'charging', 'mowing', 'full']:
            self.set_mode(requested_mode)
        else:
            self.get_logger().warn(f'Invalid mode requested: {requested_mode}')
    
    def set_mode(self, mode):
        """Set robot operational mode and configure subsystems"""
        self.current_mode = mode
        
        # Mode configurations
        if mode == 'idle':
            # Everything off except basic monitoring
            self.publish_enables(motors=False, sensors=False, gps=False, lidar=False, camera=False)
            self.get_logger().info('Mode: IDLE - All systems disabled')
            
        elif mode == 'charging':
            # Only battery monitoring active
            self.publish_enables(motors=False, sensors=True, gps=False, lidar=False, camera=False)
            self.get_logger().info('Mode: CHARGING - Battery monitoring only')
            
        elif mode == 'mowing':
            # Full autonomous mode
            self.publish_enables(motors=True, sensors=True, gps=True, lidar=True, camera=True)
            self.get_logger().info('Mode: MOWING - Full autonomous operation')
            
        elif mode == 'full':
            # Everything enabled
            self.publish_enables(motors=True, sensors=True, gps=True, lidar=True, camera=True)
            self.get_logger().info('Mode: FULL - All systems enabled')
    
    def publish_enables(self, motors, sensors, gps, lidar, camera):
        """Publish enable/disable commands to all subsystems"""
        self.motors_enable_pub.publish(Bool(data=motors))
        self.sensors_enable_pub.publish(Bool(data=sensors))
        self.gps_enable_pub.publish(Bool(data=gps))
        self.lidar_enable_pub.publish(Bool(data=lidar))
        self.camera_enable_pub.publish(Bool(data=camera))
    
    def publish_status(self):
        """Periodically publish current mode"""
        mode_msg = String()
        mode_msg.data = self.current_mode
        self.mode_pub.publish(mode_msg)


def main(args=None):
    rclpy.init(args=args)
    node = ModeManager()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
