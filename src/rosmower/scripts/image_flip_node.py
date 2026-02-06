#!/usr/bin/env python3
"""
Simple node to flip camera image 180 degrees (upside down)
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo
from cv_bridge import CvBridge
import cv2


class ImageFlipNode(Node):
    def __init__(self):
        super().__init__('image_flip_node')
        
        self.bridge = CvBridge()
        
        # Subscribe to raw camera image
        self.image_sub = self.create_subscription(
            Image,
            'image_raw_unflipped',
            self.image_callback,
            10
        )
        
        # Subscribe to camera info
        self.info_sub = self.create_subscription(
            CameraInfo,
            'camera_info_unflipped',
            self.info_callback,
            10
        )
        
        # Publish flipped image
        self.image_pub = self.create_publisher(Image, 'image_raw/flipped', 10)
        
        # Publish camera info
        self.info_pub = self.create_publisher(CameraInfo, 'camera_info', 10)
        
        self.get_logger().info('Image flip node started - rotating images 180 degrees')
    
    def image_callback(self, msg):
        try:
            # Convert ROS Image to OpenCV format
            cv_image = self.bridge.imgmsg_to_cv2(msg, desired_encoding='passthrough')
            
            # Rotate image 180 degrees
            flipped_image = cv2.rotate(cv_image, cv2.ROTATE_180)
            
            # Convert back to ROS Image message
            flipped_msg = self.bridge.cv2_to_imgmsg(flipped_image, encoding=msg.encoding)
            flipped_msg.header = msg.header
            
            # Publish flipped image
            self.image_pub.publish(flipped_msg)
            
        except Exception as e:
            self.get_logger().error(f'Error processing image: {e}')
    
    def info_callback(self, msg):
        # Just pass through the camera info
        self.info_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = ImageFlipNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
