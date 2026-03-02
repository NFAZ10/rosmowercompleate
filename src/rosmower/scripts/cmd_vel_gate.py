#!/usr/bin/env python3
"""
cmd_vel_gate — Charging safety gate for motor commands.

Sits between teleop/navigation and the motor driver. Passes /cmd_vel through
to /cmd_vel_motors normally, but zeroes it out when the charger is connected
(detected via negative current on /current from battery_splitter).

Topic flow:
  teleop/nav  →  /cmd_vel  →  [this node]  →  /cmd_vel_motors  →  VESC driver
"""

import math
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Float32


class CmdVelGate(Node):
    def __init__(self):
        super().__init__('cmd_vel_gate')

        self.declare_parameter('charging_current_threshold', -1.0)  # A; negative = charging
        self._threshold = self.get_parameter('charging_current_threshold').value

        self._is_charging = False
        self._last_current = float('nan')

        self.create_subscription(Float32, '/current', self._on_current, 10)
        self.create_subscription(Twist, '/cmd_vel', self._on_cmd_vel, 10)
        self._pub = self.create_publisher(Twist, '/cmd_vel_motors', 10)

        self.get_logger().info(
            f'cmd_vel_gate ready — charging lockout at {self._threshold:.1f}A')

    def _on_current(self, msg: Float32):
        current = float(msg.data)
        if not math.isfinite(current):
            return
        was_charging = self._is_charging
        self._is_charging = current < self._threshold
        self._last_current = current
        if self._is_charging and not was_charging:
            self.get_logger().warn(
                f'🔌 Charger detected ({current:.1f}A) — /cmd_vel BLOCKED')
            # Publish a zero Twist immediately to stop any ongoing motion
            self._pub.publish(Twist())
        elif not self._is_charging and was_charging:
            self.get_logger().info(
                f'🔋 Charger removed ({current:.1f}A) — /cmd_vel OPEN')

    def _on_cmd_vel(self, msg: Twist):
        if self._is_charging:
            # Silently drop movement commands while charging
            return
        self._pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = CmdVelGate()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
