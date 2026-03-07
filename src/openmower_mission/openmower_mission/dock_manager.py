#!/usr/bin/env python3
"""
Dock Manager — OpenMowerNext-inspired docking station manager.

Manages the dock position and handles precise return-to-dock navigation.
Supports loading dock position from file or live GPS, and publishes a
staged approach (coarse Nav2 navigation → fine alignment).

OpenMowerNext reference: docking_helper_node / DockRobotNearest action server.

Topics:
  Subscribed:
    /gps/fix            (sensor_msgs/NavSatFix)  — live GPS
    /odom               (nav_msgs/Odometry)       — robot pose in map frame
    /mission/state      (std_msgs/String)        — from mission_executor
    /robot_mode         (std_msgs/String)

  Published:
    /dock/pose          (geometry_msgs/PoseStamped)  — dock position in map frame
    /dock/status        (std_msgs/String)             — UNKNOWN/KNOWN/APPROACHING/DOCKED
    /goal_pose          (geometry_msgs/PoseStamped)  — sends Nav2 goals
    /dock/gps           (sensor_msgs/NavSatFix)      — dock GPS position (if captured)

Parameters:
  dock_file         — path to YAML file storing the dock pose
  dock_staging_dist — meters in front of dock for final approach staging pose
  approach_speed    — max approach speed (m/s)
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from geometry_msgs.msg import PoseStamped
from sensor_msgs.msg import NavSatFix
from nav_msgs.msg import Odometry

import os
import math
import yaml
from pathlib import Path
from typing import Optional


class DockStatus:
    UNKNOWN = 'UNKNOWN'
    KNOWN = 'KNOWN'
    APPROACHING = 'APPROACHING'
    DOCKED = 'DOCKED'


class DockManager(Node):
    """
    Manages docking station position and return navigation.

    Inspired by OpenMowerNext's DockRobotNearest action server.
    On DOCK_RETURN mission state, publishes a staged approach:
    1. Coarse goal: staging pose N meters in front of dock
    2. Fine goal: dock position itself (slow approach)
    """

    def __init__(self):
        super().__init__('dock_manager')

        # ── Parameters ─────────────────────────────────────────────────────
        self.declare_parameter('dock_file', '/ws/zones/dock.yaml')
        self.declare_parameter('dock_staging_dist_m', 1.5)
        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('auto_save_dock', True)

        self.dock_file = Path(self.get_parameter('dock_file').value)
        self.staging_dist = self.get_parameter('dock_staging_dist_m').value
        self.frame_id = self.get_parameter('frame_id').value
        self.auto_save = self.get_parameter('auto_save_dock').value

        # ── State ───────────────────────────────────────────────────────────
        self.dock_pose: Optional[PoseStamped] = None
        self.dock_status: str = DockStatus.UNKNOWN
        self.mission_state: str = 'IDLE'
        self.robot_mode: str = 'idle'
        self.approach_stage: int = 0   # 0=not started, 1=staging, 2=final

        # Live sensor tracking
        self.last_gps: Optional[NavSatFix] = None
        self.last_odom: Optional[Odometry] = None

        # ── Load persisted dock position ─────────────────────────────────────
        self._load_dock_from_file()

        # ── Subscribers ──────────────────────────────────────────────────────
        self.create_subscription(NavSatFix, '/gps/fix', self._gps_cb, 10)
        self.create_subscription(Odometry, '/odom', self._odom_cb, 10)
        self.create_subscription(String, '/mission/state', self._mission_state_cb, 10)
        self.create_subscription(String, '/robot_mode', self._mode_cb, 10)
        self.create_subscription(String, '/dock/command', self._dock_cmd_cb, 10)

        # ── Publishers ───────────────────────────────────────────────────────
        self.dock_pose_pub = self.create_publisher(PoseStamped, '/dock/pose', 10)
        self.dock_status_pub = self.create_publisher(String, '/dock/status', 10)
        self.dock_gps_pub = self.create_publisher(NavSatFix, '/dock/gps', 10)
        self.goal_pub = self.create_publisher(PoseStamped, '/goal_pose', 10)

        # ── Periodic status publish ───────────────────────────────────────────
        self.create_timer(2.0, self._publish_status)

        self.get_logger().info(
            f'Dock Manager started | dock_file={self.dock_file} | '
            f'status={self.dock_status}'
        )

    # ── File I/O ──────────────────────────────────────────────────────────────

    def _load_dock_from_file(self):
        """Load dock position from YAML file if it exists."""
        if not self.dock_file.exists():
            self.get_logger().info(f'No dock file found at {self.dock_file} — dock unknown')
            return

        try:
            with open(self.dock_file, 'r') as f:
                data = yaml.safe_load(f)

            pose = PoseStamped()
            pose.header.frame_id = data.get('frame_id', self.frame_id)

            # Support both map-frame x/y and GPS lat/lon storage
            if 'x' in data and 'y' in data:
                pose.pose.position.x = float(data['x'])
                pose.pose.position.y = float(data['y'])
                pose.pose.position.z = 0.0
                yaw = float(data.get('yaw', 0.0))
                pose.pose.orientation.w = math.cos(yaw / 2.0)
                pose.pose.orientation.z = math.sin(yaw / 2.0)
                self.dock_pose = pose
                self.dock_status = DockStatus.KNOWN
                self.get_logger().info(
                    f'Dock loaded from map coords: x={data["x"]:.3f} y={data["y"]:.3f} '
                    f'yaw={math.degrees(yaw):.1f}°'
                )
            elif 'lat' in data and 'lon' in data:
                # GPS-only dock — pose will be set when robot_localization is available
                self.dock_status = DockStatus.UNKNOWN
                self.get_logger().info(
                    f'Dock GPS saved: lat={data["lat"]:.7f} lon={data["lon"]:.7f} — '
                    f'map-frame x/y not yet set; set manually or use SET_DOCK_HERE when localized'
                )
            else:
                self.get_logger().warn('dock.yaml has no x/y or lat/lon — dock unknown')

        except Exception as e:
            self.get_logger().error(f'Failed to load dock file: {e}')

    def save_dock_to_file(self, pose: PoseStamped, gps: Optional[NavSatFix] = None):
        """Persist dock position to YAML, optionally including GPS coordinates."""
        try:
            self.dock_file.parent.mkdir(parents=True, exist_ok=True)
            q = pose.pose.orientation
            yaw = 2.0 * math.atan2(q.z, q.w)
            data = {
                'frame_id': pose.header.frame_id,
                'x': round(pose.pose.position.x, 4),
                'y': round(pose.pose.position.y, 4),
                'yaw': round(yaw, 4),
            }
            if gps is not None:
                data['lat'] = round(gps.latitude, 8)
                data['lon'] = round(gps.longitude, 8)
                data['alt'] = round(gps.altitude, 3)
            with open(self.dock_file, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)
            self.get_logger().info(f'Dock position saved to {self.dock_file}')
        except Exception as e:
            self.get_logger().error(f'Failed to save dock: {e}')

    def save_dock_gps_to_file(self, gps: NavSatFix):
        """Persist GPS-only dock position (no map frame coords yet)."""
        try:
            self.dock_file.parent.mkdir(parents=True, exist_ok=True)
            # Preserve existing x/y if present
            existing = {}
            if self.dock_file.exists():
                with open(self.dock_file, 'r') as f:
                    existing = yaml.safe_load(f) or {}
            existing.update({
                'lat': round(gps.latitude, 8),
                'lon': round(gps.longitude, 8),
                'alt': round(gps.altitude, 3),
                'frame_id': existing.get('frame_id', self.frame_id),
            })
            with open(self.dock_file, 'w') as f:
                yaml.dump(existing, f, default_flow_style=False)
            self.get_logger().info(
                f'Dock GPS saved: lat={gps.latitude:.7f} lon={gps.longitude:.7f}'
            )
        except Exception as e:
            self.get_logger().error(f'Failed to save dock GPS: {e}')

    # ── Subscriber Callbacks ─────────────────────────────────────────────────

    def _gps_cb(self, msg: NavSatFix):
        """Track live GPS position for dock recording."""
        if msg.status.status >= 0:  # -1 = no fix
            self.last_gps = msg

    def _odom_cb(self, msg: Odometry):
        """Track robot pose in map frame via odometry."""
        self.last_odom = msg

    def _mission_state_cb(self, msg: String):
        new_state = msg.data
        if new_state == 'DOCK_RETURN' and self.mission_state != 'DOCK_RETURN':
            self.get_logger().info('Mission → DOCK_RETURN: initiating dock approach')
            self._start_dock_approach()
        self.mission_state = new_state

    def _mode_cb(self, msg: String):
        self.robot_mode = msg.data

    def _dock_cmd_cb(self, msg: String):
        """Handle direct dock commands from web UI or other nodes."""
        cmd = msg.data.strip().upper()
        if cmd == 'SET_DOCK_HERE':
            self._set_dock_at_current_pose()
        elif cmd == 'SET_DOCK_GPS':
            self._set_dock_at_current_gps()
        elif cmd == 'RETURN_TO_DOCK':
            self._start_dock_approach()
        elif cmd == 'CLEAR_DOCK':
            self.dock_pose = None
            self.dock_status = DockStatus.UNKNOWN
            self.get_logger().info('Dock position cleared')

    # ── Dock Approach ─────────────────────────────────────────────────────────

    def _start_dock_approach(self):
        """Begin the two-stage dock approach."""
        if self.dock_pose is None:
            self.get_logger().error('Cannot return to dock — dock position unknown!')
            self.get_logger().error('Drive to dock manually and publish /dock/command: SET_DOCK_HERE')
            self.dock_status = DockStatus.UNKNOWN
            return

        self.approach_stage = 1
        self.dock_status = DockStatus.APPROACHING
        self._publish_staging_goal()

    def _publish_staging_goal(self):
        """
        Stage 1: Navigate to a point staging_dist meters in front of the dock.
        This gives the robot a clean, aligned final approach path.
        """
        if self.dock_pose is None:
            return

        # Extract dock yaw
        q = self.dock_pose.pose.orientation
        dock_yaw = 2.0 * math.atan2(q.z, q.w)

        # Compute staging point: behind the dock (robot approaches from front)
        staging = PoseStamped()
        staging.header.frame_id = self.frame_id
        staging.header.stamp = self.get_clock().now().to_msg()
        staging.pose.position.x = (
            self.dock_pose.pose.position.x - self.staging_dist * math.cos(dock_yaw)
        )
        staging.pose.position.y = (
            self.dock_pose.pose.position.y - self.staging_dist * math.sin(dock_yaw)
        )
        staging.pose.position.z = 0.0
        staging.pose.orientation = self.dock_pose.pose.orientation

        self.get_logger().info(
            f'Dock approach stage 1: staging pose at '
            f'({staging.pose.position.x:.2f}, {staging.pose.position.y:.2f})'
        )
        self.goal_pub.publish(staging)

        # Schedule final approach after delay (production: use goal feedback)
        self.create_timer(8.0, self._publish_final_dock_goal)

    def _publish_final_dock_goal(self):
        """Stage 2: Precise final approach to dock position."""
        if self.dock_pose is None or self.dock_status != DockStatus.APPROACHING:
            return

        final = PoseStamped()
        final.header.frame_id = self.frame_id
        final.header.stamp = self.get_clock().now().to_msg()
        final.pose = self.dock_pose.pose

        self.get_logger().info('Dock approach stage 2: final dock goal')
        self.goal_pub.publish(final)

        # Mark as docked after another delay (production: detect charging current)
        self.create_timer(6.0, self._mark_docked)

    def _mark_docked(self):
        """Mark robot as docked."""
        self.dock_status = DockStatus.DOCKED
        self.approach_stage = 0
        self.get_logger().info('✅ Robot docked — charging should begin')

    def _set_dock_at_current_pose(self):
        """Set dock to current odometry pose (robot must be at the dock)."""
        if self.last_odom is None:
            self.get_logger().error(
                'SET_DOCK_HERE: no odometry received yet — is /odom publishing?'
            )
            return

        pose = PoseStamped()
        pose.header.frame_id = self.frame_id
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = self.last_odom.pose.pose.position.x
        pose.pose.position.y = self.last_odom.pose.pose.position.y
        pose.pose.position.z = 0.0
        pose.pose.orientation = self.last_odom.pose.pose.orientation

        self.dock_pose = pose
        self.dock_status = DockStatus.KNOWN
        self.get_logger().info(
            f'✅ Dock set from odom: x={pose.pose.position.x:.3f} '
            f'y={pose.pose.position.y:.3f}'
        )
        if self.auto_save:
            self.save_dock_to_file(pose, gps=self.last_gps)

    def _set_dock_at_current_gps(self):
        """Save current GPS position as dock (map-frame x/y not set)."""
        if self.last_gps is None:
            self.get_logger().error(
                'SET_DOCK_GPS: no GPS fix received yet — is /gps/fix publishing?'
            )
            return
        self.save_dock_gps_to_file(self.last_gps)
        self.get_logger().info(
            f'✅ Dock GPS captured: lat={self.last_gps.latitude:.7f} '
            f'lon={self.last_gps.longitude:.7f}'
        )

    # ── Publishing ────────────────────────────────────────────────────────────

    def _publish_status(self):
        if self.dock_pose:
            self.dock_pose_pub.publish(self.dock_pose)
        # Publish saved dock GPS if available
        if self.dock_file.exists():
            try:
                import yaml as _yaml
                with open(self.dock_file, 'r') as f:
                    d = _yaml.safe_load(f)
                if d and 'lat' in d and 'lon' in d:
                    gps_msg = NavSatFix()
                    gps_msg.header.stamp = self.get_clock().now().to_msg()
                    gps_msg.header.frame_id = 'gps'
                    gps_msg.latitude = float(d['lat'])
                    gps_msg.longitude = float(d['lon'])
                    gps_msg.altitude = float(d.get('alt', 0.0))
                    gps_msg.status.status = 0
                    self.dock_gps_pub.publish(gps_msg)
            except Exception:
                pass
        msg = String()
        msg.data = self.dock_status
        self.dock_status_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = DockManager()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
