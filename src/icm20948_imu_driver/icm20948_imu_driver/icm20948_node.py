#!/usr/bin/env python3
"""
ROS2 Node for ICM20948 9-axis IMU
Publishes sensor data on standard ROS2 topics
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, MagneticField, Temperature
from std_msgs.msg import Header
from geometry_msgs.msg import Vector3
import numpy as np

try:
    from .icm20948_driver import ICM20948
except ImportError:
    from icm20948_driver import ICM20948


class ICM20948Node(Node):
    """ROS2 node for ICM20948 IMU sensor"""
    
    def __init__(self):
        super().__init__('icm20948_imu_node')
        
        # Declare parameters
        self.declare_parameter('i2c_bus', 7)
        self.declare_parameter('i2c_address', 0x68)
        self.declare_parameter('frame_id', 'imu_link')
        self.declare_parameter('publish_rate', 100.0)
        self.declare_parameter('publish_temperature', True)
        self.declare_parameter('publish_magnetometer', True)
        
        # Get parameters
        i2c_bus = self.get_parameter('i2c_bus').value
        i2c_address = self.get_parameter('i2c_address').value
        self.frame_id = self.get_parameter('frame_id').value
        publish_rate = self.get_parameter('publish_rate').value
        self.publish_temp = self.get_parameter('publish_temperature').value
        self.publish_mag = self.get_parameter('publish_magnetometer').value
        
        # Initialize IMU driver
        self.get_logger().info(f'Initializing ICM20948 on I2C bus {i2c_bus}, address 0x{i2c_address:02X}')
        self.imu = ICM20948(i2c_bus=i2c_bus, address=i2c_address)
        
        if not self.imu.initialize():
            self.get_logger().error('Failed to initialize ICM20948 sensor')
            raise RuntimeError('ICM20948 initialization failed')
            
        self.get_logger().info('ICM20948 initialized successfully')
        
        # Create publishers
        self.imu_pub = self.create_publisher(Imu, 'imu/data', 10)
        
        if self.publish_mag:
            self.mag_pub = self.create_publisher(MagneticField, 'imu/mag', 10)
            
        if self.publish_temp:
            self.temp_pub = self.create_publisher(Temperature, 'imu/temperature', 10)
        
        # Create timer for publishing
        timer_period = 1.0 / publish_rate
        self.timer = self.create_timer(timer_period, self.timer_callback)
        
        self.get_logger().info(f'Publishing IMU data at {publish_rate} Hz')
        
    def timer_callback(self):
        """Timer callback to read and publish sensor data"""
        try:
            # Read sensor data
            accel = self.imu.read_accel()
            gyro = self.imu.read_gyro()
            
            # Create IMU message
            imu_msg = Imu()
            imu_msg.header = Header()
            imu_msg.header.stamp = self.get_clock().now().to_msg()
            imu_msg.header.frame_id = self.frame_id
            
            # Linear acceleration
            imu_msg.linear_acceleration.x = accel[0]
            imu_msg.linear_acceleration.y = accel[1]
            imu_msg.linear_acceleration.z = accel[2]
            
            # Angular velocity
            imu_msg.angular_velocity.x = gyro[0]
            imu_msg.angular_velocity.y = gyro[1]
            imu_msg.angular_velocity.z = gyro[2]
            
            # Orientation is not computed (would need sensor fusion)
            imu_msg.orientation.w = 0.0
            imu_msg.orientation.x = 0.0
            imu_msg.orientation.y = 0.0
            imu_msg.orientation.z = 0.0
            
            # Covariance matrices
            # Set to -1 for orientation (unknown)
            imu_msg.orientation_covariance[0] = -1.0
            
            # Set reasonable covariances for accel and gyro
            # These values should be calibrated for your specific sensor
            accel_cov = 0.01
            gyro_cov = 0.001
            
            imu_msg.linear_acceleration_covariance = [
                accel_cov, 0.0, 0.0,
                0.0, accel_cov, 0.0,
                0.0, 0.0, accel_cov
            ]
            
            imu_msg.angular_velocity_covariance = [
                gyro_cov, 0.0, 0.0,
                0.0, gyro_cov, 0.0,
                0.0, 0.0, gyro_cov
            ]
            
            # Publish IMU data
            self.imu_pub.publish(imu_msg)
            
            # Read and publish magnetometer data
            if self.publish_mag:
                mag = self.imu.read_mag()
                mag_msg = MagneticField()
                mag_msg.header = imu_msg.header
                mag_msg.magnetic_field.x = mag[0]
                mag_msg.magnetic_field.y = mag[1]
                mag_msg.magnetic_field.z = mag[2]
                
                # Magnetometer covariance
                mag_cov = 1e-6
                mag_msg.magnetic_field_covariance = [
                    mag_cov, 0.0, 0.0,
                    0.0, mag_cov, 0.0,
                    0.0, 0.0, mag_cov
                ]
                
                self.mag_pub.publish(mag_msg)
            
            # Read and publish temperature
            if self.publish_temp:
                temp = self.imu.read_temperature()
                temp_msg = Temperature()
                temp_msg.header = imu_msg.header
                temp_msg.temperature = temp
                temp_msg.variance = 1.0
                
                self.temp_pub.publish(temp_msg)
                
        except Exception as e:
            self.get_logger().error(f'Error reading sensor data: {e}')
            
    def destroy_node(self):
        """Clean up resources"""
        self.get_logger().info('Shutting down ICM20948 node')
        self.imu.close()
        super().destroy_node()


def main(args=None):
    """Main entry point"""
    rclpy.init(args=args)
    
    try:
        node = ICM20948Node()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f'Error: {e}')
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
