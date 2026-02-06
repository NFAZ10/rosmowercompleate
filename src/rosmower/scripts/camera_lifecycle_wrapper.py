#!/usr/bin/env python3
"""
Lifecycle wrapper for camera nodes.
Controls v4l2_camera and image_flip nodes based on enable/disable commands.
"""

import rclpy
from rclpy.lifecycle import Node, State, TransitionCallbackReturn
from std_msgs.msg import Bool
import subprocess
import signal
import os


class CameraLifecycleWrapper(Node):
    def __init__(self):
        super().__init__('camera_lifecycle_wrapper')
        
        self.enabled = False
        self.camera_process = None
        self.flip_process = None
        self.transport_process = None
        
        # Subscribe to enable/disable commands
        self.enable_sub = self.create_subscription(
            Bool,
            '/enable_camera',
            self.on_enable_callback,
            10
        )
        
        self.get_logger().info('Camera lifecycle wrapper created')
    
    def on_configure(self, state: State) -> TransitionCallbackReturn:
        """Configure the wrapper."""
        self.get_logger().info('Configuring camera wrapper...')
        return TransitionCallbackReturn.SUCCESS
    
    def on_activate(self, state: State) -> TransitionCallbackReturn:
        """Activate cameras."""
        self.get_logger().info('Activating cameras...')
        self.start_camera_nodes()
        self.enabled = True
        return TransitionCallbackReturn.SUCCESS
    
    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        """Deactivate cameras."""
        self.get_logger().info('Deactivating cameras...')
        self.stop_camera_nodes()
        self.enabled = False
        return TransitionCallbackReturn.SUCCESS
    
    def on_cleanup(self, state: State) -> TransitionCallbackReturn:
        """Cleanup resources."""
        self.get_logger().info('Cleaning up camera wrapper...')
        self.stop_camera_nodes()
        return TransitionCallbackReturn.SUCCESS
    
    def on_shutdown(self, state: State) -> TransitionCallbackReturn:
        """Shutdown the wrapper."""
        self.get_logger().info('Shutting down camera wrapper...')
        self.stop_camera_nodes()
        return TransitionCallbackReturn.SUCCESS
    
    def on_enable_callback(self, msg: Bool):
        """Handle enable/disable commands."""
        if msg.data and not self.enabled:
            self.get_logger().info('Camera enable requested')
            if self.get_current_state().label == 'inactive':
                self.trigger_activate()
        elif not msg.data and self.enabled:
            self.get_logger().info('Camera disable requested')
            if self.get_current_state().label == 'active':
                self.trigger_deactivate()
    
    def start_camera_nodes(self):
        """Start camera-related nodes."""
        try:
            # Start v4l2_camera node
            self.get_logger().info('Starting v4l2_camera node...')
            self.camera_process = subprocess.Popen(
                [
                    'ros2', 'run', 'v4l2_camera', 'v4l2_camera_node',
                    '--ros-args',
                    '-r', '__ns:=/camera',
                    '-p', 'video_device:=/dev/video2',
                    '-p', 'image_size:=[640,480]',
                    '-p', 'time_per_frame:=[1,30]',
                    '-p', 'pixel_format:=YUYV',
                    '-p', 'output_encoding:=bgr8',
                    '-p', 'camera_frame_id:=camera_link_optical',
                    '-r', 'image_raw:=image_raw_unflipped',
                    '-r', 'camera_info:=camera_info_unflipped'
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Start image flip node
            self.get_logger().info('Starting image_flip node...')
            self.flip_process = subprocess.Popen(
                [
                    'ros2', 'run', 'rosmower', 'image_flip_node.py',
                    '--ros-args',
                    '-r', '__ns:=/camera'
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # Start image transport republish node
            self.get_logger().info('Starting image_transport node...')
            self.transport_process = subprocess.Popen(
                [
                    'ros2', 'run', 'image_transport', 'republish',
                    'raw', 'compressed',
                    '--ros-args',
                    '-r', '__ns:=/camera',
                    '-r', 'in:=image_raw/flipped',
                    '-r', 'out/compressed:=image_raw/compressed'
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            self.get_logger().info('Camera nodes started')
            
        except Exception as e:
            self.get_logger().error(f'Failed to start camera nodes: {e}')
    
    def stop_camera_nodes(self):
        """Stop camera-related nodes."""
        processes = [
            ('v4l2_camera', self.camera_process),
            ('image_flip', self.flip_process),
            ('image_transport', self.transport_process)
        ]
        
        for name, process in processes:
            if process and process.poll() is None:
                self.get_logger().info(f'Stopping {name} node...')
                try:
                    process.send_signal(signal.SIGINT)
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.get_logger().warn(f'{name} did not stop gracefully, killing...')
                    process.kill()
                except Exception as e:
                    self.get_logger().error(f'Error stopping {name}: {e}')
        
        self.camera_process = None
        self.flip_process = None
        self.transport_process = None
        self.get_logger().info('Camera nodes stopped')


def main(args=None):
    rclpy.init(args=args)
    wrapper = CameraLifecycleWrapper()
    
    # Configure and activate
    wrapper.trigger_configure()
    wrapper.trigger_activate()
    
    try:
        rclpy.spin(wrapper)
    except KeyboardInterrupt:
        pass
    finally:
        wrapper.trigger_deactivate()
        wrapper.trigger_cleanup()
        wrapper.trigger_shutdown()
        wrapper.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
