#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import hailo
import numpy as np

class HailoNode(Node):
    def __init__(self):
        super().__init__('hailo_node')
        
        # Initialize CV bridge
        self.cv_bridge = CvBridge()
        
        # Initialize Hailo device
        try:
            self.device = hailo.Device()
            self.get_logger().info('Successfully connected to Hailo-8 device')
        except Exception as e:
            self.get_logger().error(f'Failed to connect to Hailo device: {str(e)}')
            return
            
        # Create publishers
        self.result_pub = self.create_publisher(Image, 'hailo/output', 10)
        
        # Create subscribers
        self.create_subscription(Image, 'hailo/input', self.image_callback, 10)
        
        self.get_logger().info('Hailo ROS 2 node initialized successfully')
    
    def load_network(self, hef_path):
        """Load a network from a HEF file."""
        try:
            # Configure the device with the network
            self.hef = hailo.HEF(hef_path)
            self.configured_network = self.device.configure(self.hef)
            self.get_logger().info(f'Successfully loaded network from {hef_path}')
            return True
        except Exception as e:
            self.get_logger().error(f'Failed to load network: {str(e)}')
            return False
    
    def image_callback(self, msg):
        """Callback for processing incoming images."""
        try:
            # Convert ROS Image message to CV2
            cv_image = self.cv_bridge.imgmsg_to_cv2(msg, desired_encoding='bgr8')
            
            # TODO: Add preprocessing specific to your model
            # preprocessed_data = self.preprocess(cv_image)
            
            # Run inference
            # input_data = {input_name: preprocessed_data}
            # output_data = self.configured_network.infer(input_data)
            
            # TODO: Add postprocessing specific to your model
            # result_image = self.postprocess(output_data)
            
            # Publish results
            # result_msg = self.cv_bridge.cv2_to_imgmsg(result_image, encoding='bgr8')
            # self.result_pub.publish(result_msg)
            
        except Exception as e:
            self.get_logger().error(f'Error processing image: {str(e)}')

def main(args=None):
    rclpy.init(args=args)
    
    hailo_node = HailoNode()
    
    try:
        rclpy.spin(hailo_node)
    except KeyboardInterrupt:
        pass
    finally:
        hailo_node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
