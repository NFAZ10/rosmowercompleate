#!/usr/bin/env python3
import time
from typing import Optional

import rclpy
from rclpy.node import Node
from rclpy.time import Time
from std_srvs.srv import Empty
from sensor_msgs.msg import LaserScan

class RPLidarMotorControl(Node):
    def __init__(self):
        super().__init__('rplidar_motor_control')
        self.declare_parameter('topic_name', '/scan')
        self.declare_parameter('node1', 'rviz')
        self.declare_parameter('node2', 'move_base')
        self.declare_parameter('seconds_between_tries', 5)

        self.topic_name = self.get_parameter('topic_name').get_parameter_value().string_value
        # Legacy node-name parameters retained for compatibility with existing launch files
        self.node1 = self.get_parameter('node1').get_parameter_value().string_value
        self.node2 = self.get_parameter('node2').get_parameter_value().string_value
        self.seconds_between_tries = self.get_parameter('seconds_between_tries').get_parameter_value().integer_value

        self.last_scan_time: Optional[Time] = None
        self.last_call = time.monotonic() - float(self.seconds_between_tries)

        self.scan_sub = self.create_subscription(LaserScan, self.topic_name, self.scan_cb, 10)

        self.cli_start = self.create_client(Empty, '/start_motor')
        self.cli_stop = self.create_client(Empty, '/stop_motor')

        # Timer runs at 1 Hz
        self.timer = self.create_timer(1.0, self.timer_cb)

        # Track whether we've received a positive response from /start_motor
        self.motor_running = False

    def scan_cb(self, msg: LaserScan):
        self.last_scan_time = self.get_clock().now()

    def is_scanning(self):
        if self.last_scan_time is None:
            return False
        elapsed = self.get_clock().now() - self.last_scan_time
        return elapsed.nanoseconds < int(1e9)

    def count_external_scan_subscribers(self) -> int:
        try:
            infos = self.get_subscriptions_info_by_topic(self.topic_name)
        except Exception as exc:
            # Introspection can occasionally fail during graph changes; default to zero so the motor stays off.
            self.get_logger().warn(f'Failed to inspect subscriptions for {self.topic_name}: {exc}')
            return 0

        count = 0
        for info in infos:
            if info.node_name == self.get_name() and info.node_namespace == self.get_namespace():
                continue
            count += 1
        return count

    def timer_cb(self):
        # throttle attempts
        if (time.monotonic() - self.last_call) < float(self.seconds_between_tries):
            return

        subscriber_count = self.count_external_scan_subscribers()
        lidar_required = subscriber_count > 0

        if lidar_required and not self.motor_running:
            if self.cli_start.wait_for_service(timeout_sec=1.0):
                req = Empty.Request()
                fut = self.cli_start.call_async(req)
                rclpy.spin_until_future_complete(self, fut, timeout_sec=2.0)
                if fut.done() and not fut.exception():
                    self.get_logger().info('Called /start_motor')
                    self.motor_running = True
                else:
                    self.get_logger().error('Failed to call /start_motor')
            else:
                self.get_logger().warn('/start_motor service not available')
            self.last_call = time.monotonic()
        elif (not lidar_required) and (self.motor_running or self.is_scanning()):
            if self.cli_stop.wait_for_service(timeout_sec=1.0):
                req = Empty.Request()
                fut = self.cli_stop.call_async(req)
                rclpy.spin_until_future_complete(self, fut, timeout_sec=2.0)
                if fut.done() and not fut.exception():
                    self.get_logger().info('Called /stop_motor')
                    self.motor_running = False
                else:
                    self.get_logger().error('Failed to call /stop_motor')
            else:
                self.get_logger().warn('/stop_motor service not available')
            self.last_call = time.monotonic()


def main(args=None):
    rclpy.init(args=args)
    node = RPLidarMotorControl()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
