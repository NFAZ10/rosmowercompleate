#!/usr/bin/env python3
"""
Battery Monitor Node
Monitors battery percentage and current, triggers dock return when low
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32, String, Bool


class BatteryState:
    NORMAL = "NORMAL"
    LOW = "LOW"
    CRITICAL = "CRITICAL"
    CHARGING = "CHARGING"
    CHARGED = "CHARGED"


class BatteryMonitor(Node):
    def __init__(self):
        super().__init__('battery_monitor')
        
        # Declare parameters
        self.declare_parameter('low_battery_threshold', 25.0)
        self.declare_parameter('critical_battery_threshold', 15.0)
        self.declare_parameter('charged_threshold', 95.0)
        self.declare_parameter('charging_current_threshold', -0.1)
        
        # Get parameters
        self.low_threshold = self.get_parameter('low_battery_threshold').value
        self.critical_threshold = self.get_parameter('critical_battery_threshold').value
        self.charged_threshold = self.get_parameter('charged_threshold').value
        self.charging_current = self.get_parameter('charging_current_threshold').value
        
        # State variables
        self.battery_percent = 100.0
        self.current = 0.0
        self.state = BatteryState.NORMAL
        self.previous_state = BatteryState.NORMAL
        
        # Subscribers
        self.create_subscription(Float32, '/percent', self.battery_callback, 10)
        self.create_subscription(Float32, '/current', self.current_callback, 10)
        
        # Publishers
        self.state_pub = self.create_publisher(String, '/battery/state', 10)
        self.low_battery_pub = self.create_publisher(Bool, '/battery/low', 10)
        self.mission_cmd_pub = self.create_publisher(String, '/mission/command', 10)
        
        # Timer for periodic state updates (1 Hz)
        self.create_timer(1.0, self.update_state)
        
        # Counter for periodic logging (every 10 seconds)
        self.log_counter = 0
        
        self.get_logger().info('Battery Monitor started')
        self.get_logger().info(f'Low: {self.low_threshold}%, Critical: {self.critical_threshold}%')
        self.get_logger().info(f'Charged: {self.charged_threshold}%, Charging current threshold: {self.charging_current}A')
        
    def battery_callback(self, msg):
        """Handle battery percentage updates"""
        self.battery_percent = msg.data
        
    def current_callback(self, msg):
        """Handle battery current updates"""
        self.current = msg.data
        
    def update_state(self):
        """Update battery state based on percentage and current"""
        old_state = self.state
        
        # Check if charging (negative current indicates charging)
        if self.current < self.charging_current:
            if self.battery_percent >= self.charged_threshold:
                self.state = BatteryState.CHARGED
            else:
                self.state = BatteryState.CHARGING
        # Check battery level when not charging
        elif self.battery_percent < self.critical_threshold:
            self.state = BatteryState.CRITICAL
        elif self.battery_percent < self.low_threshold:
            self.state = BatteryState.LOW
        else:
            self.state = BatteryState.NORMAL
        
        # State transition logic
        if old_state != self.state:
            self.get_logger().info(f'Battery state changed: {old_state} -> {self.state}')
            
            # Trigger mission commands on critical transitions
            if self.state == BatteryState.CRITICAL and old_state not in [BatteryState.CHARGING, BatteryState.CHARGED]:
                self.get_logger().error('⚠️  CRITICAL BATTERY! Emergency dock!')
                cmd = String()
                cmd.data = 'EMERGENCY_DOCK'
                self.mission_cmd_pub.publish(cmd)
                
            elif self.state == BatteryState.LOW and old_state == BatteryState.NORMAL:
                self.get_logger().warn('🔋 Low battery detected, should return to dock')
                cmd = String()
                cmd.data = 'RETURN_TO_DOCK'
                self.mission_cmd_pub.publish(cmd)
                
            elif self.state == BatteryState.CHARGED and old_state == BatteryState.CHARGING:
                self.get_logger().info('✅ Battery fully charged, ready to resume')
                cmd = String()
                cmd.data = 'BATTERY_CHARGED'
                self.mission_cmd_pub.publish(cmd)
        
        # Publish current state
        state_msg = String()
        state_msg.data = self.state
        self.state_pub.publish(state_msg)
        
        # Publish low battery flag
        low_msg = Bool()
        low_msg.data = (self.state in [BatteryState.LOW, BatteryState.CRITICAL])
        self.low_battery_pub.publish(low_msg)
        
        # Log status periodically (every 10 seconds)
        self.log_counter += 1
        if self.log_counter >= 10:
            self.log_counter = 0
            self.get_logger().info(
                f'Battery: {self.battery_percent:.1f}%, '
                f'Current: {self.current:.2f}A, '
                f'State: {self.state}'
            )


def main(args=None):
    rclpy.init(args=args)
    node = BatteryMonitor()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
