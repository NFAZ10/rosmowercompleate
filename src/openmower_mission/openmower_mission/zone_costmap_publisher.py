#!/usr/bin/env python3
"""
Zone Costmap Publisher — OpenMowerNext-inspired area-type costmap integration.

Converts Zone exclusion/navigation/operation areas into Nav2 costmap updates.
Exclusion zones → LETHAL_OBSTACLE (255)
Navigation corridors → FREE_SPACE (0)
Operation zones → low cost (1) — robot mows here

OpenMowerNext reference: area types in behavior tree and costmap config.

Topics:
  Subscribed: /zones (rosmower_msgs/ZoneArray)
  Published:  /costmap_updates (nav2_msgs concept — OccupancyGrid)
              /zone_markers (visualization_msgs/MarkerArray)
"""

import rclpy
from rclpy.node import Node
from nav_msgs.msg import OccupancyGrid
from visualization_msgs.msg import MarkerArray, Marker
from geometry_msgs.msg import Point
from std_msgs.msg import ColorRGBA, String
from rosmower_msgs.msg import ZoneArray, Zone

import math
from typing import Dict, List, Tuple


# Zone type constants (extend Zone.msg with these when ready)
ZONE_TYPE_OPERATION = 0    # mow here
ZONE_TYPE_NAVIGATION = 1   # transit only, no mowing
ZONE_TYPE_EXCLUSION = 2    # never enter — lethal cost

# Costmap values
COST_FREE = 0
COST_OPERATION = 1
COST_NAVIGATION = 10
COST_EXCLUSION = 100   # OccupancyGrid max is 100


class ZoneCostmapPublisher(Node):
    """
    Publishes zone areas as OccupancyGrid costmap and RViz visualization markers.

    This enables Nav2 to respect exclusion zones (ponds, flower beds) and
    prefer navigation corridors when planning paths between mowing areas.

    Zone type is read from zone.name prefix convention until Zone.msg is extended:
      [EXCL] Zone name  → exclusion
      [NAV] Zone name   → navigation corridor
      (no prefix)       → operation (mow here)
    """

    def __init__(self):
        super().__init__('zone_costmap_publisher')

        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('resolution', 0.1)   # meters per cell
        self.declare_parameter('map_width_m', 100.0)
        self.declare_parameter('map_height_m', 100.0)
        self.declare_parameter('map_origin_x', -50.0)
        self.declare_parameter('map_origin_y', -50.0)
        self.declare_parameter('publish_rate_hz', 0.5)

        self.frame_id = self.get_parameter('frame_id').value
        self.resolution = self.get_parameter('resolution').value
        self.map_w = int(self.get_parameter('map_width_m').value / self.resolution)
        self.map_h = int(self.get_parameter('map_height_m').value / self.resolution)
        self.origin_x = self.get_parameter('map_origin_x').value
        self.origin_y = self.get_parameter('map_origin_y').value

        self.zones: Dict[str, Zone] = {}

        self.create_subscription(ZoneArray, '/zones', self._zones_cb, 10)

        self.costmap_pub = self.create_publisher(OccupancyGrid, '/zone_costmap', 10)
        self.marker_pub = self.create_publisher(MarkerArray, '/zone_markers', 10)

        hz = self.get_parameter('publish_rate_hz').value
        self.create_timer(1.0 / hz, self._publish)

        self.get_logger().info(
            f'Zone Costmap Publisher ready | '
            f'{self.map_w}x{self.map_h} cells @ {self.resolution}m/cell'
        )

    def _zones_cb(self, msg: ZoneArray):
        for zone in msg.zones:
            self.zones[zone.id] = zone

    def _get_zone_type(self, zone: Zone) -> int:
        """Determine zone type from name prefix convention."""
        name = zone.name.upper()
        if name.startswith('[EXCL]') or name.startswith('EXCL:'):
            return ZONE_TYPE_EXCLUSION
        elif name.startswith('[NAV]') or name.startswith('NAV:'):
            return ZONE_TYPE_NAVIGATION
        return ZONE_TYPE_OPERATION

    def _zone_cost(self, zone_type: int) -> int:
        if zone_type == ZONE_TYPE_EXCLUSION:
            return COST_EXCLUSION
        elif zone_type == ZONE_TYPE_NAVIGATION:
            return COST_NAVIGATION
        return COST_OPERATION

    def _point_in_polygon(self, px: float, py: float, pts: List[Tuple[float, float]]) -> bool:
        """Ray-casting point-in-polygon test."""
        n = len(pts)
        inside = False
        j = n - 1
        for i in range(n):
            xi, yi = pts[i]
            xj, yj = pts[j]
            if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi + 1e-10) + xi):
                inside = not inside
            j = i
        return inside

    def _build_costmap(self) -> OccupancyGrid:
        grid = OccupancyGrid()
        grid.header.frame_id = self.frame_id
        grid.header.stamp = self.get_clock().now().to_msg()
        grid.info.resolution = self.resolution
        grid.info.width = self.map_w
        grid.info.height = self.map_h
        grid.info.origin.position.x = self.origin_x
        grid.info.origin.position.y = self.origin_y
        grid.info.origin.orientation.w = 1.0

        data = [-1] * (self.map_w * self.map_h)   # -1 = unknown

        for zone in self.zones.values():
            if not zone.enabled:
                continue
            pts = [(p.x, p.y) for p in zone.polygon.polygon.points]
            if len(pts) < 3:
                continue

            zone_type = self._get_zone_type(zone)
            cost = self._zone_cost(zone_type)

            # Bounding box for efficiency
            min_x = min(p[0] for p in pts)
            max_x = max(p[0] for p in pts)
            min_y = min(p[1] for p in pts)
            max_y = max(p[1] for p in pts)

            # Convert to grid indices
            col_min = max(0, int((min_x - self.origin_x) / self.resolution) - 1)
            col_max = min(self.map_w - 1, int((max_x - self.origin_x) / self.resolution) + 1)
            row_min = max(0, int((min_y - self.origin_y) / self.resolution) - 1)
            row_max = min(self.map_h - 1, int((max_y - self.origin_y) / self.resolution) + 1)

            for row in range(row_min, row_max + 1):
                for col in range(col_min, col_max + 1):
                    wx = self.origin_x + col * self.resolution
                    wy = self.origin_y + row * self.resolution
                    if self._point_in_polygon(wx, wy, pts):
                        idx = row * self.map_w + col
                        data[idx] = cost

        grid.data = data
        return grid

    def _build_markers(self) -> MarkerArray:
        """Build RViz visualization markers for all zones."""
        arr = MarkerArray()

        # Zone type → color
        type_colors = {
            ZONE_TYPE_OPERATION: (0.2, 0.8, 0.2, 0.3),   # green
            ZONE_TYPE_NAVIGATION: (0.2, 0.2, 0.8, 0.3),  # blue
            ZONE_TYPE_EXCLUSION: (0.8, 0.2, 0.2, 0.5),   # red
        }

        for i, zone in enumerate(self.zones.values()):
            if not zone.enabled:
                continue

            pts = list(zone.polygon.polygon.points)
            if len(pts) < 3:
                continue

            zone_type = self._get_zone_type(zone)
            r, g, b, a = type_colors.get(zone_type, (0.5, 0.5, 0.5, 0.3))

            # Filled polygon marker
            m = Marker()
            m.header.frame_id = self.frame_id
            m.header.stamp = self.get_clock().now().to_msg()
            m.ns = 'zones'
            m.id = i
            m.type = Marker.LINE_STRIP
            m.action = Marker.ADD
            m.scale.x = 0.05
            m.color = ColorRGBA(r=r, g=g, b=b, a=1.0)

            for pt in pts:
                p = Point()
                p.x = pt.x
                p.y = pt.y
                p.z = 0.05
                m.points.append(p)
            # Close the loop
            if pts:
                p = Point()
                p.x = pts[0].x
                p.y = pts[0].y
                p.z = 0.05
                m.points.append(p)

            arr.markers.append(m)

            # Zone label
            label = Marker()
            label.header = m.header
            label.ns = 'zone_labels'
            label.id = i + 10000
            label.type = Marker.TEXT_VIEW_FACING
            label.action = Marker.ADD
            if pts:
                cx = sum(p.x for p in pts) / len(pts)
                cy = sum(p.y for p in pts) / len(pts)
                label.pose.position.x = cx
                label.pose.position.y = cy
                label.pose.position.z = 0.3
            label.scale.z = 0.4
            label.color = ColorRGBA(r=1.0, g=1.0, b=1.0, a=1.0)
            label.text = zone.name
            arr.markers.append(label)

        return arr

    def _publish(self):
        if not self.zones:
            return
        self.costmap_pub.publish(self._build_costmap())
        self.marker_pub.publish(self._build_markers())


def main(args=None):
    rclpy.init(args=args)
    node = ZoneCostmapPublisher()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
