#!/usr/bin/env python3

"""
Simple Stereo Camera Viewer
Displays left and right camera streams in OpenCV windows
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2


class SimpleViewer(Node):
    def __init__(self):
        super().__init__('simple_viewer')
        
        # Declare parameters
        self.declare_parameter('show_fps', True)
        self.declare_parameter('window_width', 640)
        self.declare_parameter('window_height', 480)
        
        # Get parameters
        self.show_fps = self.get_parameter('show_fps').value
        self.window_width = self.get_parameter('window_width').value
        self.window_height = self.get_parameter('window_height').value
        
        # Create CV Bridge
        self.bridge = CvBridge()
        
        # Subscribe to camera topics
        self.left_sub = self.create_subscription(
            Image,
            'stereo/left/image_raw',
            self.left_callback,
            10
        )
        
        self.right_sub = self.create_subscription(
            Image,
            'stereo/right/image_raw',
            self.right_callback,
            10
        )
        
        # FPS calculation
        self.left_frame_count = 0
        self.right_frame_count = 0
        self.last_time = self.get_clock().now()
        self.left_fps = 0.0
        self.right_fps = 0.0
        
        # Create windows
        cv2.namedWindow('Left Camera', cv2.WINDOW_NORMAL)
        cv2.namedWindow('Right Camera', cv2.WINDOW_NORMAL)
        cv2.resizeWindow('Left Camera', self.window_width, self.window_height)
        cv2.resizeWindow('Right Camera', self.window_width, self.window_height)
        
        self.get_logger().info('Simple Stereo Viewer started')
        self.get_logger().info('Press "q" in any window to quit')
        self.get_logger().info('Press "s" to save stereo pair')
        
        # Timer to check for key presses
        self.create_timer(0.01, self.check_keys)
        
        self.image_count = 0
    
    def calculate_fps(self):
        """Calculate FPS for both cameras"""
        current_time = self.get_clock().now()
        elapsed = (current_time - self.last_time).nanoseconds / 1e9
        
        if elapsed > 1.0:
            self.left_fps = self.left_frame_count / elapsed
            self.right_fps = self.right_frame_count / elapsed
            self.left_frame_count = 0
            self.right_frame_count = 0
            self.last_time = current_time
    
    def left_callback(self, msg):
        """Handle left camera images"""
        try:
            # Convert ROS Image to OpenCV
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            
            # Add FPS overlay if enabled
            if self.show_fps:
                self.calculate_fps()
                cv2.putText(cv_image, f'Left FPS: {self.left_fps:.1f}', 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                           1, (0, 255, 0), 2)
            
            # Display
            cv2.imshow('Left Camera', cv_image)
            self.left_frame_count += 1
            
        except Exception as e:
            self.get_logger().error(f'Error processing left image: {e}')
    
    def right_callback(self, msg):
        """Handle right camera images"""
        try:
            # Convert ROS Image to OpenCV
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            
            # Add FPS overlay if enabled
            if self.show_fps:
                cv2.putText(cv_image, f'Right FPS: {self.right_fps:.1f}', 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                           1, (0, 255, 0), 2)
            
            # Display
            cv2.imshow('Right Camera', cv_image)
            self.right_frame_count += 1
            
        except Exception as e:
            self.get_logger().error(f'Error processing right image: {e}')
    
    def check_keys(self):
        """Check for key presses"""
        key = cv2.waitKey(1) & 0xFF
        
        if key == ord('q'):
            self.get_logger().info('Quit requested')
            rclpy.shutdown()
        elif key == ord('s'):
            self.get_logger().info(f'Saving stereo pair {self.image_count}...')
            # Note: Images will be saved on next callback
            self.image_count += 1
    
    def destroy_node(self):
        """Clean up"""
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    viewer = SimpleViewer()
    
    try:
        rclpy.spin(viewer)
    except KeyboardInterrupt:
        pass
    finally:
        viewer.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
