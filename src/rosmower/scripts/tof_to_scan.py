#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from sensor_msgs.msg import LaserScan
import math

# Channel mapping: ch0=left(+90°), ch1=right(-90°), ch2=front(0°)
CHANNEL_ANGLES = {
    0: math.radians(90),   # ch0 = left
    1: math.radians(-90),  # ch1 = right  
    2: math.radians(0),    # ch2 = front
}

class ToFScan(Node):
    def __init__(self):
        super().__init__('tof_to_scan')
        self.sub = self.create_subscription(String, 'vl53_distances', self.cb, 10)
        self.pub = self.create_publisher(LaserScan, 'scan', 10)
        self.get_logger().info("ToF -> LaserScan bridge started")

    def cb(self, msg: String):
        # expected: "ch0=123,ch1=456,ch2=789"
        parts = msg.data.split(',')
        if len(parts) < 3:
            return

        # parse distances by channel (mm -> meters)
        channel_distances = {}
        for i, p in enumerate(parts[:3]):
            val = p.split('=')[1].strip() if '=' in p else ""
            try:
                channel_distances[i] = float(val) / 1000.0
            except ValueError:
                channel_distances[i] = float('inf')

        # Sort channels by angle (angle_min to angle_max)
        # ch1(right,-90°) -> ch2(front,0°) -> ch0(left,+90°)
        sorted_channels = sorted(CHANNEL_ANGLES.items(), key=lambda x: x[1])
        ranges_ordered = [channel_distances.get(ch, float('inf')) for ch, _ in sorted_channels]
        
        scan = LaserScan()
        scan.header.stamp = self.get_clock().now().to_msg()
        scan.header.frame_id = "base_link"
        scan.angle_min = sorted_channels[0][1]  # -90° (right)
        scan.angle_max = sorted_channels[-1][1]  # +90° (left)
        scan.angle_increment = (scan.angle_max - scan.angle_min) / (len(ranges_ordered) - 1)
        scan.range_min = 0.02
        scan.range_max = 2.0
        scan.ranges = ranges_ordered

        self.pub.publish(scan)

def main(args=None):
    rclpy.init(args=args)
    node = ToFScan()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
