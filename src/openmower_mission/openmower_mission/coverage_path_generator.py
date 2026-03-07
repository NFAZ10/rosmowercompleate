#!/usr/bin/env python3
"""
Coverage Path Generator — OpenMowerNext-inspired boustrophedon (lawnmower stripe) coverage planner.

Takes a Zone polygon and generates a nav_msgs/Path of stripe waypoints the robot
follows to achieve full-area coverage. Supports configurable stripe width, overlap,
and approach angle.

Topics:
  Subscribed: /zones (rosmower_msgs/ZoneArray)
  Published:  /coverage/path (nav_msgs/Path)
              /coverage/status (std_msgs/String)

Services:
  /coverage/generate_path  (rosmower_msgs/GenerateCoveragePath)
"""

import rclpy
from rclpy.node import Node
from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped, Quaternion
from std_msgs.msg import String
from rosmower_msgs.msg import ZoneArray, Zone

import math
import numpy as np
from shapely.geometry import Polygon, LineString, MultiLineString, Point
from shapely.ops import unary_union


def yaw_to_quaternion(yaw: float) -> Quaternion:
    """Convert a yaw angle (radians) to a geometry_msgs/Quaternion."""
    q = Quaternion()
    q.w = math.cos(yaw / 2.0)
    q.z = math.sin(yaw / 2.0)
    q.x = 0.0
    q.y = 0.0
    return q


class CoveragePathGenerator(Node):
    """
    Generates boustrophedon (back-and-forth stripe) coverage paths for mowing zones.

    Inspired by OpenMowerNext's ComputeCoveragePath behavior tree node.
    Uses the Shapely geometry library to compute stripe intersections with
    the zone polygon, then emits them as a nav_msgs/Path.
    """

    def __init__(self):
        super().__init__('coverage_path_generator')

        # Parameters
        self.declare_parameter('stripe_width_m', 0.28)       # mower deck width (m)
        self.declare_parameter('overlap_m', 0.04)            # stripe overlap (m)
        self.declare_parameter('approach_angle_deg', 0.0)    # stripe direction
        self.declare_parameter('waypoint_spacing_m', 0.25)   # pose density along stripes
        self.declare_parameter('frame_id', 'map')

        self.stripe_width = self.get_parameter('stripe_width_m').value
        self.overlap = self.get_parameter('overlap_m').value
        self.angle_deg = self.get_parameter('approach_angle_deg').value
        self.spacing = self.get_parameter('waypoint_spacing_m').value
        self.frame_id = self.get_parameter('frame_id').value

        # Effective spacing between stripes
        self.stripe_spacing = self.stripe_width - self.overlap

        # State
        self.zones = {}        # zone_id → Zone msg
        self.active_zone_id = None

        # Subscribers
        self.create_subscription(ZoneArray, '/zones', self._zones_callback, 10)
        self.create_subscription(String, '/coverage/request_zone', self._request_callback, 10)

        # Publishers
        self.path_pub = self.create_publisher(Path, '/coverage/path', 10)
        self.status_pub = self.create_publisher(String, '/coverage/status', 10)

        self.get_logger().info(
            f'Coverage Path Generator ready | '
            f'stripe={self.stripe_width}m overlap={self.overlap}m '
            f'angle={self.angle_deg}°'
        )

    # ── Callbacks ────────────────────────────────────────────────────────────

    def _zones_callback(self, msg: ZoneArray):
        for zone in msg.zones:
            self.zones[zone.id] = zone

    def _request_callback(self, msg: String):
        """Generate and publish a coverage path for the requested zone ID."""
        zone_id = msg.data.strip()
        if zone_id not in self.zones:
            self.get_logger().error(f'Zone "{zone_id}" not found. Known: {list(self.zones.keys())}')
            self._publish_status(f'ERROR:zone_not_found:{zone_id}')
            return

        self.get_logger().info(f'Generating coverage path for zone: {zone_id}')
        path = self.generate_for_zone(self.zones[zone_id])

        if path and len(path.poses) > 0:
            self.path_pub.publish(path)
            self._publish_status(f'READY:{zone_id}:{len(path.poses)}_waypoints')
            self.get_logger().info(
                f'Published coverage path: {len(path.poses)} waypoints for zone {zone_id}'
            )
        else:
            self.get_logger().error(f'Failed to generate path for zone {zone_id}')
            self._publish_status(f'ERROR:generation_failed:{zone_id}')

    # ── Core Algorithm ────────────────────────────────────────────────────────

    def generate_for_zone(self, zone: Zone) -> Path:
        """
        Generate a boustrophedon path for the given zone polygon.

        Algorithm:
        1. Extract polygon from Zone message
        2. Rotate polygon to align with stripe direction
        3. Sweep horizontal scan-lines at stripe_spacing intervals
        4. Intersect scan-lines with polygon to get stripe segments
        5. Order stripes for minimal travel (boustrophedon: alternate direction)
        6. Rotate waypoints back to map frame
        7. Pack into nav_msgs/Path
        """
        pts = [(p.x, p.y) for p in zone.polygon.polygon.points]
        if len(pts) < 3:
            self.get_logger().error('Zone polygon has fewer than 3 points')
            return Path()

        poly = Polygon(pts)
        if not poly.is_valid:
            poly = poly.buffer(0)   # repair self-intersections

        angle_rad = math.radians(self.angle_deg)
        stripes = self._compute_stripes(poly, angle_rad)

        if not stripes:
            self.get_logger().warn('No stripes generated — zone may be too small')
            return Path()

        path = Path()
        path.header.frame_id = self.frame_id
        path.header.stamp = self.get_clock().now().to_msg()

        for i, stripe in enumerate(stripes):
            # Alternate direction for boustrophedon pattern
            coords = list(stripe.coords)
            if i % 2 == 1:
                coords = coords[::-1]

            # Sample poses along the stripe
            segment = LineString(coords)
            poses = self._sample_line(segment, angle_rad if i % 2 == 0 else angle_rad + math.pi)
            path.poses.extend(poses)

        return path

    def _compute_stripes(self, poly: Polygon, angle_rad: float):
        """Compute scan-line stripe segments intersected with the polygon."""
        # Rotate polygon so stripes are horizontal
        rotated = self._rotate_polygon(poly, -angle_rad)
        min_y, max_y = rotated.bounds[1], rotated.bounds[3]
        min_x, max_x = rotated.bounds[0], rotated.bounds[2]

        stripes = []
        y = min_y + self.stripe_spacing / 2.0

        while y <= max_y:
            scan_line = LineString([(min_x - 1.0, y), (max_x + 1.0, y)])
            intersection = rotated.intersection(scan_line)

            if intersection.is_empty:
                y += self.stripe_spacing
                continue

            # Handle both single LineString and MultiLineString
            if intersection.geom_type == 'LineString':
                segments = [intersection]
            elif intersection.geom_type == 'MultiLineString':
                segments = list(intersection.geoms)
            else:
                y += self.stripe_spacing
                continue

            for seg in segments:
                if seg.length > self.stripe_spacing * 0.5:
                    # Rotate segment back to map frame
                    rotated_seg = self._rotate_linestring(seg, angle_rad)
                    stripes.append(rotated_seg)

            y += self.stripe_spacing

        return stripes

    def _rotate_polygon(self, poly: Polygon, angle: float) -> Polygon:
        """Rotate a polygon around its centroid."""
        cx, cy = poly.centroid.x, poly.centroid.y
        pts = []
        for x, y in poly.exterior.coords:
            rx = cx + (x - cx) * math.cos(angle) - (y - cy) * math.sin(angle)
            ry = cy + (x - cx) * math.sin(angle) + (y - cy) * math.cos(angle)
            pts.append((rx, ry))
        return Polygon(pts)

    def _rotate_linestring(self, line: LineString, angle: float) -> LineString:
        """Rotate a LineString around the origin."""
        pts = []
        for x, y in line.coords:
            rx = x * math.cos(angle) - y * math.sin(angle)
            ry = x * math.sin(angle) + y * math.cos(angle)
            pts.append((rx, ry))
        return LineString(pts)

    def _sample_line(self, line: LineString, heading: float):
        """Sample PoseStamped waypoints along a LineString at self.spacing intervals."""
        poses = []
        q = yaw_to_quaternion(heading)
        total = line.length
        d = 0.0

        while d <= total:
            pt = line.interpolate(d)
            pose = PoseStamped()
            pose.header.frame_id = self.frame_id
            pose.header.stamp = self.get_clock().now().to_msg()
            pose.pose.position.x = pt.x
            pose.pose.position.y = pt.y
            pose.pose.position.z = 0.0
            pose.pose.orientation = q
            poses.append(pose)
            d += self.spacing

        # Always include the endpoint
        if d - self.spacing < total:
            pt = line.interpolate(total)
            pose = PoseStamped()
            pose.header.frame_id = self.frame_id
            pose.header.stamp = self.get_clock().now().to_msg()
            pose.pose.position.x = pt.x
            pose.pose.position.y = pt.y
            pose.pose.position.z = 0.0
            pose.pose.orientation = q
            poses.append(pose)

        return poses

    def _publish_status(self, status: str):
        msg = String()
        msg.data = status
        self.status_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = CoveragePathGenerator()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
