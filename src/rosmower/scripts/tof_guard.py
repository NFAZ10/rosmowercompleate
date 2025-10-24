#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import Twist
import time

class ToFGuard(Node):
    def __init__(self):
        super().__init__('tof_guard')
        
        # Parameters
        self.declare_parameter('min_distance_mm', 200)  # default minimum safe distance in mm
        self.declare_parameter('min_distances_by_channel', [200, 200, 200])  # per-channel thresholds [ch0, ch1, ch2]
        self.declare_parameter('cmd_vel_in', '/cmd_vel_in')
        self.declare_parameter('cmd_vel_out', '/cmd_vel')
        self.declare_parameter('cooldown_s', 0.5)  # cooldown period after obstacle cleared
        
        # Use per-channel distances if provided, otherwise use default for all
        channel_distances = self.get_parameter('min_distances_by_channel').value
        default_distance = self.get_parameter('min_distance_mm').value
        
        # Ensure we have distances for at least 3 channels (ch0, ch1, ch2)
        if len(channel_distances) < 3:
            channel_distances.extend([default_distance] * (3 - len(channel_distances)))
        
        self.min_distances_by_channel = {i: channel_distances[i] for i in range(len(channel_distances))}
        self.cmd_vel_in_topic = self.get_parameter('cmd_vel_in').value
        self.cmd_vel_out_topic = self.get_parameter('cmd_vel_out').value
        self.cooldown_s = self.get_parameter('cooldown_s').value
        
        # Subscribers and publishers
        self.vl53_sub = self.create_subscription(String, 'vl53_distances', self.vl53_callback, 10)
        self.cmd_vel_sub = self.create_subscription(Twist, self.cmd_vel_in_topic, self.cmd_vel_callback, 10)
        self.cmd_vel_pub = self.create_publisher(Twist, self.cmd_vel_out_topic, 10)
        
        # State variables
        self.obstacle_detected = False
        self.last_clear_time = time.time()
        self.current_cmd_vel = Twist()
        self.channel_distances = {}  # Store latest distances by channel
        
        # Log startup info
        threshold_info = ', '.join([f'ch{ch}:{dist}mm' for ch, dist in self.min_distances_by_channel.items()])
        self.get_logger().info(f'ToF Guard started - thresholds: {threshold_info}')
        self.get_logger().info(f'Input: {self.cmd_vel_in_topic} -> Output: {self.cmd_vel_out_topic}')

    def vl53_callback(self, msg: String):
        """Parse VL53 distance data and check for obstacles"""
        # Parse format: "ch0=123,ch1=456,ch2=789"
        parts = msg.data.split(',')
        
        obstacle_detected_now = False
        min_distance = float('inf')
        closest_channel = None
        
        for part in parts:
            if '=' in part:
                try:
                    channel_str, distance_str = part.split('=', 1)
                    channel = int(channel_str.replace('ch', ''))
                    distance_mm = float(distance_str.strip())
                    
                    self.channel_distances[channel] = distance_mm
                    
                    # Get threshold for this specific channel
                    channel_threshold = self.min_distances_by_channel.get(channel, 200)  # default to 200mm
                    
                    # Check if this distance is below threshold
                    if distance_mm < channel_threshold and distance_mm > 0:
                        obstacle_detected_now = True
                        if distance_mm < min_distance:
                            min_distance = distance_mm
                            closest_channel = channel
                            
                except (ValueError, IndexError) as e:
                    self.get_logger().debug(f'Failed to parse distance data: {part} - {e}')
                    continue
        
        # Update obstacle state
        if obstacle_detected_now:
            if not self.obstacle_detected:
                channel_threshold = self.min_distances_by_channel.get(closest_channel, 200)
                self.get_logger().warning(f'OBSTACLE DETECTED! Channel {closest_channel}: {min_distance:.0f}mm < {channel_threshold}mm - STOPPING')
            self.obstacle_detected = True
        else:
            if self.obstacle_detected:
                self.last_clear_time = time.time()
                self.get_logger().info('Obstacle cleared - starting cooldown period')
            self.obstacle_detected = False

    def cmd_vel_callback(self, msg: Twist):
        """Handle incoming velocity commands and apply safety filtering"""
        self.current_cmd_vel = msg
        
        # Determine if we should allow movement
        should_stop = False
        
        if self.obstacle_detected:
            should_stop = True
            reason = "obstacle detected"
        elif time.time() - self.last_clear_time < self.cooldown_s:
            should_stop = True
            remaining_cooldown = self.cooldown_s - (time.time() - self.last_clear_time)
            reason = f"cooldown ({remaining_cooldown:.1f}s remaining)"
        
        if should_stop:
            # Publish zero velocity
            stop_cmd = Twist()
            self.cmd_vel_pub.publish(stop_cmd)
            if hasattr(self, '_last_stop_reason') and self._last_stop_reason != reason:
                self.get_logger().debug(f'Movement blocked: {reason}')
            self._last_stop_reason = reason
        else:
            # Forward the original command
            self.cmd_vel_pub.publish(msg)
            if hasattr(self, '_last_stop_reason'):
                self.get_logger().info('Movement resumed - all clear')
                delattr(self, '_last_stop_reason')

    def get_status_string(self):
        """Get current status for debugging"""
        distances_str = ', '.join([f'ch{ch}:{dist:.0f}mm' for ch, dist in sorted(self.channel_distances.items())])
        return f'Distances: [{distances_str}] | Obstacle: {self.obstacle_detected}'

def main(args=None):
    rclpy.init(args=args)
    node = ToFGuard()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
