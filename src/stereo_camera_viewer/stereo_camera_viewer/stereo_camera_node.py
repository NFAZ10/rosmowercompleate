#!/usr/bin/env python3

"""
Stereo Camera Node for Jetson
Publishes left and right camera streams using GStreamer for hardware acceleration
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image, CameraInfo, CompressedImage
from std_msgs.msg import Header
from cv_bridge import CvBridge
import cv2
import numpy as np


class StereoCameraNode(Node):
    def __init__(self):
        super().__init__('stereo_camera_node')
        
        # Declare parameters
        self.declare_parameter('left_camera_id', 0)
        self.declare_parameter('right_camera_id', 1)
        self.declare_parameter('width', 1280)
        self.declare_parameter('height', 720)
        self.declare_parameter('fps', 30)
        self.declare_parameter('frame_id', 'stereo_camera')
        self.declare_parameter('use_gstreamer', True)
        self.declare_parameter('flip_method', 0)  # 0=none, 2=rotate-180, etc.
        self.declare_parameter('jpeg_quality', 80)  # Quality for compressed images
        self.declare_parameter('publish_raw', True)  # Publish raw images (disable for low-resource systems)
        
        # Get parameters
        self.left_camera_id = self.get_parameter('left_camera_id').value
        self.right_camera_id = self.get_parameter('right_camera_id').value
        self.width = self.get_parameter('width').value
        self.height = self.get_parameter('height').value
        self.fps = self.get_parameter('fps').value
        self.frame_id = self.get_parameter('frame_id').value
        self.use_gstreamer = self.get_parameter('use_gstreamer').value
        self.flip_method = self.get_parameter('flip_method').value
        self.jpeg_quality = self.get_parameter('jpeg_quality').value
        self.publish_raw = self.get_parameter('publish_raw').value
        
        # Create CV Bridge
        self.bridge = CvBridge()
        
        # Publishers - raw images
        self.left_image_pub = self.create_publisher(Image, 'stereo/left/image_raw', 10)
        self.right_image_pub = self.create_publisher(Image, 'stereo/right/image_raw', 10)
        self.left_info_pub = self.create_publisher(CameraInfo, 'stereo/left/camera_info', 10)
        self.right_info_pub = self.create_publisher(CameraInfo, 'stereo/right/camera_info', 10)
        
        # Publishers - compressed images
        self.left_compressed_pub = self.create_publisher(CompressedImage, 'stereo/left/image_raw/compressed', 10)
        self.right_compressed_pub = self.create_publisher(CompressedImage, 'stereo/right/image_raw/compressed', 10)
        
        # Initialize cameras
        self.left_cap = None
        self.right_cap = None
        self.init_cameras()
        
        # Create timer for capturing frames
        timer_period = 1.0 / self.fps
        self.timer = self.create_timer(timer_period, self.capture_and_publish)
        
        self.get_logger().info(f'Stereo Camera Node started')
        self.get_logger().info(f'Left camera ID: {self.left_camera_id}, Right camera ID: {self.right_camera_id}')
        self.get_logger().info(f'Resolution: {self.width}x{self.height} @ {self.fps} FPS')
        self.get_logger().info(f'Backend: {"GStreamer (HW accel)" if self.use_gstreamer else "V4L2"}')
        self.get_logger().info(f'Publishing: {"Raw + Compressed" if self.publish_raw else "Compressed only"}')
        self.get_logger().info(f'JPEG quality: {self.jpeg_quality}%')
    
    def gstreamer_pipeline(self, sensor_id, flip_method=0):
        """
        Create GStreamer pipeline for CSI cameras on Jetson
        Uses hardware-accelerated nvarguscamerasrc + nvvidconv for efficient processing
        
        sensor-id: 0 or 1 for IMX219 cameras on Jetson Orin Nano
        """
        return (
            f'nvarguscamerasrc sensor-id={sensor_id} ! '
            f'video/x-raw(memory:NVMM), width=(int){self.width}, height=(int){self.height}, '
            f'format=(string)NV12, framerate=(fraction){self.fps}/1 ! '
            f'nvvidconv flip-method={flip_method} ! '
            f'video/x-raw, width=(int){self.width}, height=(int){self.height}, format=(string)BGRx ! '
            f'videoconvert ! '
            f'video/x-raw, format=(string)BGR ! '
            f'appsink drop=true max-buffers=1'
        )
    
    def init_cameras(self):
        """Initialize camera captures using GStreamer or V4L2"""
        try:
            if self.use_gstreamer:
                # Use hardware-accelerated GStreamer for Jetson CSI cameras
                self.get_logger().info('Opening cameras with GStreamer (hardware-accelerated)...')
                
                # Create GStreamer pipelines for both cameras
                left_pipeline = self.gstreamer_pipeline(
                    sensor_id=self.left_camera_id,
                    flip_method=self.flip_method
                )
                right_pipeline = self.gstreamer_pipeline(
                    sensor_id=self.right_camera_id,
                    flip_method=self.flip_method
                )
                
                self.get_logger().info(f'Left pipeline: {left_pipeline}')
                self.get_logger().info(f'Right pipeline: {right_pipeline}')
                
                # Open cameras with GStreamer backend
                self.left_cap = cv2.VideoCapture(left_pipeline, cv2.CAP_GSTREAMER)
                self.right_cap = cv2.VideoCapture(right_pipeline, cv2.CAP_GSTREAMER)
                
                # GStreamer doesn't need format negotiation - pipeline handles it
                left_ok = self.left_cap and self.left_cap.isOpened()
                right_ok = self.right_cap and self.right_cap.isOpened()
                
                if left_ok:
                    self.get_logger().info('Left camera opened with GStreamer')
                else:
                    self.get_logger().error('Failed to open left camera with GStreamer')
                    
                if right_ok:
                    self.get_logger().info('Right camera opened with GStreamer')
                else:
                    self.get_logger().error('Failed to open right camera with GStreamer')
                
            else:
                # Fallback to V4L2 for USB cameras or debugging
                self.get_logger().info('Opening cameras with V4L2...')
                
                # Open cameras with V4L2 backend
                self.left_cap = cv2.VideoCapture(f'/dev/video{self.left_camera_id}', cv2.CAP_V4L2)
                self.right_cap = cv2.VideoCapture(f'/dev/video{self.right_camera_id}', cv2.CAP_V4L2)
                
                if self.left_cap.isOpened():
                    # Try different FOURCC formats for compatibility
                    formats_to_try = [
                        cv2.VideoWriter_fourcc('R', 'G', '1', '0'),  # RG10 - Bayer format
                        cv2.VideoWriter_fourcc('Y', 'U', 'Y', 'V'),  # YUYV
                        cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'),  # MJPEG
                    ]
                    
                    success = False
                    for fourcc in formats_to_try:
                        self.left_cap.set(cv2.CAP_PROP_FOURCC, fourcc)
                        self.left_cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                        self.left_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                        self.left_cap.set(cv2.CAP_PROP_FPS, self.fps)
                        
                        # Test if we can read a frame
                        ret, _ = self.left_cap.read()
                        if ret:
                            self.get_logger().info(f'Left camera working with FOURCC: {fourcc}')
                            success = True
                            break
                        
                    if not success:
                        self.get_logger().warn('Left camera opened but cannot read frames')
                
                if self.right_cap.isOpened():
                    # Try different FOURCC formats
                    formats_to_try = [
                        cv2.VideoWriter_fourcc('R', 'G', '1', '0'),  # RG10 - Bayer format
                        cv2.VideoWriter_fourcc('Y', 'U', 'Y', 'V'),  # YUYV
                        cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'),  # MJPEG
                    ]
                    
                    success = False
                    for fourcc in formats_to_try:
                        self.right_cap.set(cv2.CAP_PROP_FOURCC, fourcc)
                        self.right_cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                        self.right_cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                        self.right_cap.set(cv2.CAP_PROP_FPS, self.fps)
                        
                        # Test if we can read a frame
                        ret, _ = self.right_cap.read()
                        if ret:
                            self.get_logger().info(f'Right camera working with FOURCC: {fourcc}')
                            success = True
                            break
                        
                    if not success:
                        self.get_logger().warn('Right camera opened but cannot read frames')
            
            # Report final status
            left_ok = self.left_cap and self.left_cap.isOpened()
            right_ok = self.right_cap and self.right_cap.isOpened()
            
            if left_ok and right_ok:
                self.get_logger().info('✓ Both cameras opened successfully!')
            elif left_ok:
                self.get_logger().warn('⚠ Only left camera opened - right camera not available')
            elif right_ok:
                self.get_logger().warn('⚠ Only right camera opened - left camera not available')
            else:
                self.get_logger().error('✗ Failed to open cameras!')
                if self.use_gstreamer:
                    self.get_logger().error('Try: gst-launch-1.0 nvarguscamerasrc sensor-id=0 ! fakesink')
                else:
                    self.get_logger().error('Try: v4l2-ctl --list-devices')
                
            if left_ok and not self.use_gstreamer:
                # Read actual V4L2 settings (GStreamer handles this internally)
                actual_width = self.left_cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                actual_height = self.left_cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                actual_fps = self.left_cap.get(cv2.CAP_PROP_FPS)
                self.get_logger().info(f'V4L2 settings: {int(actual_width)}x{int(actual_height)} @ {actual_fps:.1f} fps')
                
        except Exception as e:
            self.get_logger().error(f'Error initializing cameras: {e}')
            import traceback
            self.get_logger().error(traceback.format_exc())
    
    def create_camera_info(self, header):
        """Create basic CameraInfo message"""
        camera_info = CameraInfo()
        camera_info.header = header
        camera_info.width = self.width
        camera_info.height = self.height
        
        # Default calibration (should be replaced with actual calibration)
        camera_info.distortion_model = "plumb_bob"
        camera_info.d = [0.0, 0.0, 0.0, 0.0, 0.0]
        
        # Default camera matrix (identity-like)
        # Reasonable defaults for IMX219
        fx = float(self.width)
        fy = float(self.width)
        cx = float(self.width) / 2.0
        cy = float(self.height) / 2.0
        
        camera_info.k = [
            fx, 0.0, cx,
            0.0, fy, cy,
            0.0, 0.0, 1.0
        ]
        
        camera_info.r = [
            1.0, 0.0, 0.0,
            0.0, 1.0, 0.0,
            0.0, 0.0, 1.0
        ]
        
        camera_info.p = [
            fx, 0.0, cx, 0.0,
            0.0, fy, cy, 0.0,
            0.0, 0.0, 1.0, 0.0
        ]
        
        return camera_info
    
    def _process_frame(self, frame):
        """Debayer raw Bayer frames; BGR frames (YUYV/MJPG) pass through unchanged."""
        if not self.use_gstreamer and frame is not None:
            try:
                # Only debayer if frame is single-channel (true raw Bayer, e.g. RG10).
                # Multi-channel frames are already BGR (converted by OpenCV from YUYV/MJPG).
                if frame.ndim == 2 or (frame.ndim == 3 and frame.shape[2] == 1):
                    gray = frame.reshape(frame.shape[0], frame.shape[1])
                    # Scale 10-bit Bayer values to 8-bit before debayering
                    gray8 = (gray.astype(np.uint16) >> 2).astype(np.uint8)
                    frame = cv2.cvtColor(gray8, cv2.COLOR_BAYER_RG2BGR)
            except Exception:
                pass
        return frame

    def create_compressed_image(self, frame, header):
        """Create a CompressedImage message from a cv2 frame"""
        compressed_msg = CompressedImage()
        compressed_msg.header = header
        compressed_msg.format = "jpeg"
        
        # Encode frame as JPEG
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
        result, encoded_img = cv2.imencode('.jpg', frame, encode_param)
        
        if result:
            compressed_msg.data = encoded_img.tobytes()
        
        return compressed_msg
    
    def capture_and_publish(self):
        """Capture frames from both cameras and publish"""
        # Check if at least one camera is available
        left_ok = self.left_cap and self.left_cap.isOpened()
        right_ok = self.right_cap and self.right_cap.isOpened()
        
        if not left_ok and not right_ok:
            self.get_logger().warn('No cameras opened, attempting to reinitialize...', throttle_duration_sec=5.0)
            self.init_cameras()
            return
        
        try:
            # Capture left frame if available
            ret_left, frame_left = None, None
            if left_ok:
                ret_left, frame_left = self.left_cap.read()
            
            # Capture right frame if available
            ret_right, frame_right = None, None
            if right_ok:
                ret_right, frame_right = self.right_cap.read()
            
            # Publish available frames
            if ret_left and frame_left is not None:
                frame_left = self._process_frame(frame_left)
                # Create timestamp
                timestamp = self.get_clock().now().to_msg()
                
                # Create header
                header = Header()
                header.stamp = timestamp
                header.frame_id = self.frame_id
                
                # Publish left raw image ONLY if enabled
                if self.publish_raw:
                    left_msg = self.bridge.cv2_to_imgmsg(frame_left, encoding='bgr8')
                    left_msg.header = header
                    self.left_image_pub.publish(left_msg)
                
                # Always publish compressed image (efficient)
                left_compressed = self.create_compressed_image(frame_left, header)
                self.left_compressed_pub.publish(left_compressed)
                
                # Publish left camera info
                left_info = self.create_camera_info(header)
                self.left_info_pub.publish(left_info)
            
            if ret_right and frame_right is not None:
                frame_right = self._process_frame(frame_right)
                # Create timestamp
                timestamp = self.get_clock().now().to_msg()
                
                # Create header
                header = Header()
                header.stamp = timestamp
                header.frame_id = self.frame_id
                
                # Publish right raw image ONLY if enabled
                if self.publish_raw:
                    right_msg = self.bridge.cv2_to_imgmsg(frame_right, encoding='bgr8')
                    right_msg.header = header
                    self.right_image_pub.publish(right_msg)
                
                # Always publish compressed image (efficient)
                right_compressed = self.create_compressed_image(frame_right, header)
                self.right_compressed_pub.publish(right_compressed)
                
                # Publish right camera info
                right_info = self.create_camera_info(header)
                self.right_info_pub.publish(right_info)
                    
        except Exception as e:
            self.get_logger().error(f'Error capturing frames: {e}')
    
    def destroy_node(self):
        """Clean up when node is destroyed"""
        if self.left_cap:
            self.left_cap.release()
        if self.right_cap:
            self.right_cap.release()
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = StereoCameraNode()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
