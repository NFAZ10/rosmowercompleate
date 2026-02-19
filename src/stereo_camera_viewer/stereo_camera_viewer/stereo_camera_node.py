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
import subprocess
import threading
import io


class StereoCameraNode(Node):
    def __init__(self):
        super().__init__('stereo_camera_node')
        
        # Declare parameters
        self.declare_parameter('left_camera_id', 0)
        self.declare_parameter('right_camera_id', 1)
        # nvarguscamerasrc sensor-id (0=CAM0/left, 1=CAM1/right).
        # Separate from V4L2 device ID since /dev/video numbering may differ.
        self.declare_parameter('left_sensor_id', 0)
        self.declare_parameter('right_sensor_id', 1)
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
        self.left_sensor_id = self.get_parameter('left_sensor_id').value
        self.right_sensor_id = self.get_parameter('right_sensor_id').value
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
        
        # Raw V4L2 subprocess readers for RG10 (uint16 Bayer) — used when use_gstreamer=False
        self.left_v4l2_proc = None
        self.right_v4l2_proc = None
        # Frame size for full-sensor RG10 output (3280x2464 × 2 bytes/pixel)
        self._v4l2_raw_width = 3280
        self._v4l2_raw_height = 2464
        self._v4l2_frame_bytes = self._v4l2_raw_width * self._v4l2_raw_height * 2
        
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
        Create GStreamer pipeline for CSI cameras on Jetson using nvarguscamerasrc.
        Works headlessly — no EGL/display required for appsink capture.
        sensor_id: 0 or 1 for IMX219 cameras (CSI port index, not /dev/video number)
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
    
    def _start_v4l2_raw(self, device_id):
        """
        Start a v4l2-ctl streaming subprocess to read raw RG10 (uint16 Bayer) frames.
        The Tegra V4L2 driver always outputs 3280x2464 at RG10 regardless of requested size.
        Returns the subprocess, or None on failure.
        """
        try:
            proc = subprocess.Popen(
                ['v4l2-ctl', '-d', f'/dev/video{device_id}',
                 '--stream-mmap', '--stream-count=0', '--stream-to=-'],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0
            )
            self.get_logger().info(f'Started V4L2 raw reader for /dev/video{device_id} (pid={proc.pid})')
            return proc
        except Exception as e:
            self.get_logger().error(f'Failed to start V4L2 reader for /dev/video{device_id}: {e}')
            return None

    def _read_v4l2_raw_frame(self, proc):
        """
        Read one raw RG10 frame from a v4l2-ctl subprocess and decode to BGR8.
        IMX219 outputs 10-bit Bayer (RGGB) MSB-aligned in uint16.
        Full sensor: 3280x2464 → center-crop to requested width x height.
        Returns decoded BGR frame or None on error.
        """
        try:
            raw = proc.stdout.read(self._v4l2_frame_bytes)
            if len(raw) != self._v4l2_frame_bytes:
                return None
            # Parse as uint16 (2 bytes per pixel, little-endian)
            bayer16 = np.frombuffer(raw, dtype=np.uint16).reshape(
                self._v4l2_raw_height, self._v4l2_raw_width)
            # IMX219 RG10 on Tegra: 10-bit value is MSB-aligned in 16-bit word → shift >>8 for 8-bit
            bayer8 = (bayer16 >> 8).astype(np.uint8)
            # Debayer: IMX219 is RGGB pattern → OpenCV COLOR_BAYER_RG2BGR
            bgr_full = cv2.cvtColor(bayer8, cv2.COLOR_BAYER_RG2BGR)
            # Center-crop from 3280x2464 to target resolution
            cy = (self._v4l2_raw_height - self.height) // 2
            cx = (self._v4l2_raw_width - self.width) // 2
            frame = bgr_full[cy:cy + self.height, cx:cx + self.width]
            return frame
        except Exception as e:
            self.get_logger().error(f'Error reading V4L2 raw frame: {e}', throttle_duration_sec=5.0)
            return None

    def init_cameras(self):
        """Initialize camera captures using GStreamer or V4L2"""
        try:
            if self.use_gstreamer:
                # Use hardware-accelerated GStreamer for Jetson CSI cameras
                self.get_logger().info('Opening cameras with GStreamer (nvarguscamerasrc)...')
                
                # Use sensor_id (CSI port index 0/1), not V4L2 device number
                left_pipeline = self.gstreamer_pipeline(
                    sensor_id=self.left_sensor_id,
                    flip_method=self.flip_method
                )
                right_pipeline = self.gstreamer_pipeline(
                    sensor_id=self.right_sensor_id,
                    flip_method=self.flip_method
                )
                
                self.get_logger().info(f'Left pipeline: {left_pipeline}')
                self.get_logger().info(f'Right pipeline: {right_pipeline}')
                
                # Open cameras with GStreamer backend
                self.left_cap = cv2.VideoCapture(left_pipeline, cv2.CAP_GSTREAMER)
                self.right_cap = cv2.VideoCapture(right_pipeline, cv2.CAP_GSTREAMER)
                
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
                # V4L2 raw mode: IMX219 only outputs RG10 (uint16 Bayer).
                # OpenCV cannot decode RG10 correctly, so use v4l2-ctl subprocess.
                self.get_logger().info('Opening cameras with V4L2 raw reader (RG10 uint16 Bayer)...')
                self.left_v4l2_proc = self._start_v4l2_raw(self.left_camera_id)
                self.right_v4l2_proc = self._start_v4l2_raw(self.right_camera_id)
                
                left_ok = self.left_v4l2_proc is not None
                right_ok = self.right_v4l2_proc is not None
            
            # Report final status
            if not self.use_gstreamer:
                left_ok = self.left_v4l2_proc is not None
                right_ok = self.right_v4l2_proc is not None
            else:
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
                
            if left_ok and self.use_gstreamer:
                actual_width = self.left_cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                actual_height = self.left_cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                actual_fps = self.left_cap.get(cv2.CAP_PROP_FPS)
                self.get_logger().info(f'GStreamer settings: {int(actual_width)}x{int(actual_height)} @ {actual_fps:.1f} fps')
                
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
        """GStreamer frames arrive as BGR8 — pass through unchanged."""
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
        if self.use_gstreamer:
            left_ok = self.left_cap and self.left_cap.isOpened()
            right_ok = self.right_cap and self.right_cap.isOpened()
        else:
            left_ok = self.left_v4l2_proc is not None
            right_ok = self.right_v4l2_proc is not None
        
        if not left_ok and not right_ok:
            self.get_logger().warn('No cameras available, attempting to reinitialize...', throttle_duration_sec=5.0)
            self.init_cameras()
            return
        
        try:
            # Capture left frame
            frame_left = None
            if left_ok:
                if self.use_gstreamer:
                    ret, frame_left = self.left_cap.read()
                    if not ret:
                        frame_left = None
                else:
                    frame_left = self._read_v4l2_raw_frame(self.left_v4l2_proc)
            
            # Capture right frame
            frame_right = None
            if right_ok:
                if self.use_gstreamer:
                    ret, frame_right = self.right_cap.read()
                    if not ret:
                        frame_right = None
                else:
                    frame_right = self._read_v4l2_raw_frame(self.right_v4l2_proc)
            
            # Publish available frames
            if frame_left is not None:
                frame_left = self._process_frame(frame_left)
                timestamp = self.get_clock().now().to_msg()
                header = Header()
                header.stamp = timestamp
                header.frame_id = self.frame_id
                
                if self.publish_raw:
                    left_msg = self.bridge.cv2_to_imgmsg(frame_left, encoding='bgr8')
                    left_msg.header = header
                    self.left_image_pub.publish(left_msg)
                
                left_compressed = self.create_compressed_image(frame_left, header)
                self.left_compressed_pub.publish(left_compressed)
                
                left_info = self.create_camera_info(header)
                self.left_info_pub.publish(left_info)
            
            if frame_right is not None:
                frame_right = self._process_frame(frame_right)
                timestamp = self.get_clock().now().to_msg()
                header = Header()
                header.stamp = timestamp
                header.frame_id = self.frame_id
                
                if self.publish_raw:
                    right_msg = self.bridge.cv2_to_imgmsg(frame_right, encoding='bgr8')
                    right_msg.header = header
                    self.right_image_pub.publish(right_msg)
                
                right_compressed = self.create_compressed_image(frame_right, header)
                self.right_compressed_pub.publish(right_compressed)
                
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
        if self.left_v4l2_proc:
            self.left_v4l2_proc.terminate()
        if self.right_v4l2_proc:
            self.right_v4l2_proc.terminate()
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
