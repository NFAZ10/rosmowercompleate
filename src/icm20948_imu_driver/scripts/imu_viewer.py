#!/usr/bin/env python3
"""
Simple IMU data viewer
Subscribes to IMU topics and displays data in real-time
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, MagneticField, Temperature
import sys


class IMUViewer(Node):
    """Simple IMU data viewer node"""
    
    def __init__(self):
        super().__init__('imu_viewer')
        
        # Create subscriptions
        self.imu_sub = self.create_subscription(
            Imu, 'imu/data_raw', self.imu_callback, 10)
        self.mag_sub = self.create_subscription(
            MagneticField, 'imu/mag', self.mag_callback, 10)
        self.temp_sub = self.create_subscription(
            Temperature, 'imu/temperature', self.temp_callback, 10)
        
        self.imu_data = None
        self.mag_data = None
        self.temp_data = None
        
        # Create timer for display
        self.timer = self.create_timer(0.5, self.display_callback)
        
        self.get_logger().info('IMU Viewer started. Waiting for data...')
        
    def imu_callback(self, msg):
        """IMU message callback"""
        self.imu_data = msg
        
    def mag_callback(self, msg):
        """Magnetometer message callback"""
        self.mag_data = msg
        
    def temp_callback(self, msg):
        """Temperature message callback"""
        self.temp_data = msg
        
    def display_callback(self):
        """Display current sensor data"""
        # Clear screen
        print("\033[2J\033[H")  # ANSI escape codes
        
        print("=" * 70)
        print(" ICM20948 IMU Data Viewer".center(70))
        print("=" * 70)
        
        # Display IMU data
        if self.imu_data:
            accel = self.imu_data.linear_acceleration
            gyro = self.imu_data.angular_velocity
            
            print("\n📊 ACCELEROMETER (m/s²):")
            print(f"  X: {accel.x:8.3f}  Y: {accel.y:8.3f}  Z: {accel.z:8.3f}")
            
            print("\n🔄 GYROSCOPE (rad/s):")
            print(f"  X: {gyro.x:8.3f}  Y: {gyro.y:8.3f}  Z: {gyro.z:8.3f}")
        else:
            print("\n⚠️  No IMU data received")
        
        # Display magnetometer data
        if self.mag_data:
            mag = self.mag_data.magnetic_field
            print("\n🧭 MAGNETOMETER (Tesla):")
            print(f"  X: {mag.x:10.6f}  Y: {mag.y:10.6f}  Z: {mag.z:10.6f}")
        else:
            print("\n⚠️  No magnetometer data received")
        
        # Display temperature
        if self.temp_data:
            temp = self.temp_data.temperature
            print(f"\n🌡️  TEMPERATURE: {temp:.2f} °C")
        else:
            print("\n⚠️  No temperature data received")
        
        print("\n" + "=" * 70)
        print("Press Ctrl+C to exit")


def main(args=None):
    """Main entry point"""
    rclpy.init(args=args)
    
    try:
        viewer = IMUViewer()
        rclpy.spin(viewer)
    except KeyboardInterrupt:
        print("\n\nShutting down IMU viewer...")
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
