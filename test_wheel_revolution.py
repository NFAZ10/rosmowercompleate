#!/usr/bin/env python3
"""
Test script to rotate wheels exactly one revolution.
Use this to verify wheel circumference by watching a tape mark.
Robot should be on a stand with wheels free to spin.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
import math
import time

class WheelRevolutionTest(Node):
    def __init__(self):
        super().__init__('wheel_revolution_test')
        self.publisher = self.create_publisher(Twist, '/cmd_vel', 10)
        
        # Robot parameters (should match hoverboard_bridge_node settings)
        self.wheel_radius = 0.4364  # meters (108" circumference, calibrated)
        self.wheel_separation = 0.52  # meters
        self.max_pwm = 50  # Match your launch file setting
        self.max_lin = 3.0  # Match your launch file setting
        
    def rotate_left_wheel_one_revolution(self, target_speed=0.3):
        """
        Rotate BOTH wheels exactly one revolution (robot on stand, driving straight).
        
        Args:
            target_speed: Linear velocity in m/s (default: 0.3 m/s)
        """
        # Calculate wheel circumference
        wheel_circumference = 2 * math.pi * self.wheel_radius
        
        # Time for one revolution at target speed
        time_for_one_rev = wheel_circumference / target_speed
        
        # Drive straight forward - both wheels rotate together
        cmd_v = target_speed
        cmd_w = 0.0  # No rotation, go straight
        
        print(f"\n{'='*60}")
        print(f"BOTH WHEELS REVOLUTION TEST (Robot on Stand)")
        print(f"{'='*60}")
        print(f"Wheel circumference: {wheel_circumference:.4f} m ({wheel_circumference * 39.3701:.2f} inches)")
        print(f"Expected: 27 inches")
        print(f"Target speed: {target_speed:.3f} m/s")
        print(f"Duration: {time_for_one_rev:.2f} seconds")
        print(f"\nCommand: linear.x={cmd_v:.3f} m/s, angular.z={cmd_w:.3f} rad/s")
        print(f"\nBOTH wheels will rotate one revolution together.")
        print(f"Watch your tape marker - it should return to the same position.")
        print(f"\nStarting in 3 seconds...")
        print(f"{'='*60}\n")
        
        # Countdown
        for i in range(3, 0, -1):
            print(f"{i}...")
            time.sleep(1)
        
        print("ROTATING BOTH WHEELS NOW!")
        
        # Create twist message - straight forward
        cmd = Twist()
        cmd.linear.x = cmd_v
        cmd.angular.z = cmd_w
        
        # Publish at high rate during the rotation
        start_time = time.time()
        dt = 0.02  # 50 Hz = 20ms
        
        while (time.time() - start_time) < time_for_one_rev:
            self.publisher.publish(cmd)
            time.sleep(dt)
        
        # Stop
        stop_cmd = Twist()
        for _ in range(10):  # Send stop command multiple times
            self.publisher.publish(stop_cmd)
            time.sleep(dt)
        
        print("\nDONE! Did the tape return to the starting position?")
        print(f"{'='*60}\n")


def main():
    rclpy.init()
    node = WheelRevolutionTest()
    
    try:
        print("\nThis will spin BOTH WHEELS one complete revolution together.")
        print("\nMake sure:")
        print("  1. The robot is ON and motors are ARMED")
        print("  2. The robot is ON A STAND (wheels can spin freely)")
        print("  3. You have a tape mark on a wheel to track rotation")
        
        input("\nPress ENTER when ready...")
        
        # Start with 0.3 m/s (slow and steady)
        node.rotate_left_wheel_one_revolution(target_speed=0.3)
    except KeyboardInterrupt:
        print("\nTest interrupted!")
    finally:
        # Make sure robot stops
        stop_cmd = Twist()
        for _ in range(20):
            node.publisher.publish(stop_cmd)
            time.sleep(0.02)
        
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
