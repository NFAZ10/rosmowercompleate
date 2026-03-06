#!/usr/bin/env python3
"""
GPS-Based Zone Recorder Node
Records zone boundaries by walking/driving the robot around the perimeter
with intelligent waypoint sampling, polygon simplification, and GPS quality monitoring.

Features:
- Intelligent waypoint sampling (only records when position changes significantly)
- Douglas-Peucker polygon simplification
- Real-time area calculation using Shoelace formula
- GPS quality monitoring (RTK, 3D fix, etc.)
- Pause/resume capability
- Visual odometry integration placeholder for future Isaac ROS stereo cameras
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import NavSatFix, NavSatStatus
from geometry_msgs.msg import PolygonStamped, Point32, PoseStamped
from nav_msgs.msg import Path
from std_msgs.msg import Header, String
from rosmower_msgs.msg import Zone, ZoneRecordingStatus
from rosmower_msgs.srv import (
    StartZoneRecording, StopZoneRecording, ControlZoneRecording,
    SaveZone
)
import math
import numpy as np
from datetime import datetime
from typing import List, Tuple, Optional
import pyproj
from collections import deque


class GPSWaypoint:
    """Represents a GPS waypoint with metadata"""
    def __init__(self, lat: float, lon: float, alt: float, 
                 accuracy: float, timestamp: float):
        self.lat = lat
        self.lon = lon
        self.alt = alt
        self.accuracy = accuracy
        self.timestamp = timestamp
        # Local XY coordinates (calculated later)
        self.x = 0.0
        self.y = 0.0


class ZoneRecorder(Node):
    """
    ROS2 node for recording zone boundaries using GPS waypoints.
    
    Subscribes to GPS fix data and provides services to start/stop/control recording.
    Implements intelligent sampling, polygon simplification, and area calculation.
    """
    
    # Recording states
    STATE_IDLE = 0
    STATE_RECORDING = 1
    STATE_PAUSED = 2
    
    # GPS quality levels (from sensor_msgs/NavSatFix)
    GPS_NO_FIX = -1
    GPS_FIX_2D = 0
    GPS_FIX_3D = 1
    GPS_FIX_RTK_FLOAT = 2
    GPS_FIX_RTK_FIXED = 9  # Some GPS systems use 4 or 9 for RTK fixed
    
    def __init__(self):
        super().__init__('zone_recorder')
        
        # Declare parameters
        self.declare_parameter('waypoint_min_distance', 0.5)  # meters
        self.declare_parameter('simplification_tolerance', 0.3)  # meters
        self.declare_parameter('gps_accuracy_threshold', 5.0)  # meters (5.0 works for standard GPS; use 0.1 with RTK)
        self.declare_parameter('visual_odometry_enabled', False)
        self.declare_parameter('frame_id', 'map')
        self.declare_parameter('publish_rate', 2.0)  # Hz
        self.declare_parameter('gps_topic', '/gps/fix')
        self.declare_parameter('visual_odom_topic', '/visual_odometry/pose')
        
        # Get parameters
        self.min_distance = self.get_parameter('waypoint_min_distance').value
        self.simplification_tol = self.get_parameter('simplification_tolerance').value
        self.gps_accuracy_threshold = self.get_parameter('gps_accuracy_threshold').value
        self.visual_odom_enabled = self.get_parameter('visual_odometry_enabled').value
        self.frame_id = self.get_parameter('frame_id').value
        self.publish_rate = self.get_parameter('publish_rate').value
        self.gps_topic = self.get_parameter('gps_topic').value
        self.visual_odom_topic = self.get_parameter('visual_odom_topic').value
        
        # Recording state
        self.state = self.STATE_IDLE
        self.zone_name = ""
        self.zone_priority = 5
        self.waypoints: List[GPSWaypoint] = []
        self.start_time = None
        self.last_waypoint_time = None
        self.total_distance = 0.0
        
        # GPS state
        self.current_gps: Optional[NavSatFix] = None
        self.gps_quality = 0
        self.gps_accuracy = 999.0
        self.last_recorded_lat = None
        self.last_recorded_lon = None
        
        # Visual odometry state (for future Isaac ROS integration)
        self.visual_odom_available = False
        self.current_visual_pose: Optional[PoseStamped] = None
        
        # Coordinate transformation
        # We'll use a local UTM projection for accurate distance/area calculations
        self.utm_projection = None
        self.reference_lat = None
        self.reference_lon = None
        
        # Status tracking
        self.status_message = "Ready to record"
        
        # Subscribers
        self.gps_sub = self.create_subscription(
            NavSatFix,
            self.gps_topic,
            self.gps_callback,
            10
        )
        
        # TODO: Isaac ROS Integration - Visual Odometry Subscriber
        # Uncomment when Isaac ROS stereo camera is integrated
        if self.visual_odom_enabled:
            self.visual_odom_sub = self.create_subscription(
                PoseStamped,
                self.visual_odom_topic,
                self.visual_odom_callback,
                10
            )
            self.get_logger().info(f'Visual odometry enabled, subscribing to {self.visual_odom_topic}')
        
        # Publishers
        self.status_pub = self.create_publisher(
            ZoneRecordingStatus,
            '/zone/record/status',
            10
        )
        
        self.waypoints_pub = self.create_publisher(
            Path,
            '/zone/record/waypoints',
            10
        )
        
        self.polygon_pub = self.create_publisher(
            PolygonStamped,
            '/zone/record/polygon',
            10
        )
        
        self.state_string_pub = self.create_publisher(
            String,
            '/zone/record/state',
            10
        )
        
        # Services
        self.start_srv = self.create_service(
            StartZoneRecording,
            '/zone/record/start',
            self.start_recording_callback
        )
        
        self.stop_srv = self.create_service(
            StopZoneRecording,
            '/zone/record/stop',
            self.stop_recording_callback
        )
        
        self.control_srv = self.create_service(
            ControlZoneRecording,
            '/zone/record/control',
            self.control_recording_callback
        )
        
        # Service client for saving zones
        self.save_zone_client = self.create_client(SaveZone, '/zone/save')
        
        # Timer for publishing status
        self.timer = self.create_timer(1.0 / self.publish_rate, self.publish_status)
        
        self.get_logger().info('Zone Recorder Node started')
        self.get_logger().info(f'  Min waypoint distance: {self.min_distance}m')
        self.get_logger().info(f'  Simplification tolerance: {self.simplification_tol}m')
        self.get_logger().info(f'  GPS accuracy threshold: {self.gps_accuracy_threshold}m')
        self.get_logger().info(f'  Visual odometry: {"enabled" if self.visual_odom_enabled else "disabled"}')
        
    def gps_callback(self, msg: NavSatFix):
        """Process incoming GPS fix messages"""
        self.current_gps = msg
        
        # Update GPS quality metrics
        self.gps_quality = self._determine_gps_quality(msg)
        
        # Estimate horizontal accuracy from covariance if available
        if len(msg.position_covariance) == 9:
            # Horizontal accuracy is roughly sqrt(cov_xx + cov_yy)
            self.gps_accuracy = math.sqrt(
                msg.position_covariance[0] + msg.position_covariance[4]
            )
        else:
            # Use status as rough estimate
            if msg.status.status == NavSatFix.STATUS_GBAS_FIX:  # RTK
                self.gps_accuracy = 0.02
            elif msg.status.status == NavSatFix.STATUS_SBAS_FIX:
                self.gps_accuracy = 0.5
            elif msg.status.status == NavSatFix.STATUS_FIX:
                self.gps_accuracy = 2.0
            else:
                self.gps_accuracy = 999.0
        
        # If recording, check if we should record this waypoint
        if self.state == self.STATE_RECORDING:
            self._try_record_waypoint(msg)
    
    def visual_odom_callback(self, msg: PoseStamped):
        """
        Process visual odometry messages (from Isaac ROS stereo cameras)
        
        TODO: Isaac ROS Integration
        - Use visual odometry to refine waypoint positions when GPS accuracy is poor
        - Implement sensor fusion between GPS and visual odometry
        - Handle transitions between GPS and visual odometry
        """
        self.current_visual_pose = msg
        self.visual_odom_available = True
        # Future: Implement GPS/visual odometry fusion here
    
    def _determine_gps_quality(self, msg: NavSatFix) -> int:
        """Determine GPS quality level from NavSatFix message"""
        status = msg.status.status
        
        # Map NavSatStatus constants to our quality levels
        if status == NavSatStatus.STATUS_NO_FIX:
            return 0  # No fix
        elif status == NavSatStatus.STATUS_FIX:
            # Could be 2D or 3D, check covariance
            if len(msg.position_covariance) == 9 and msg.position_covariance[8] < 100:
                return 2  # 3D fix (reasonable altitude accuracy)
            return 1  # 2D fix
        elif status == NavSatStatus.STATUS_SBAS_FIX:
            return 2  # 3D SBAS fix
        elif status == NavSatStatus.STATUS_GBAS_FIX:
            # RTK fix - check if float or fixed
            if self.gps_accuracy < 0.05:
                return 4  # RTK fixed
            else:
                return 3  # RTK float
        
        return 0
    
    def _try_record_waypoint(self, msg: NavSatFix):
        """Try to record a waypoint if conditions are met"""
        # Check GPS accuracy
        if self.gps_accuracy > self.gps_accuracy_threshold:
            self.status_message = f"GPS accuracy poor ({self.gps_accuracy:.2f}m), waiting for better signal"
            return
        
        # Check if we have a valid position
        if math.isnan(msg.latitude) or math.isnan(msg.longitude):
            self.status_message = "Invalid GPS position"
            return
        
        # Check distance from last waypoint
        if self.last_recorded_lat is not None and self.last_recorded_lon is not None:
            distance = self._haversine_distance(
                self.last_recorded_lat, self.last_recorded_lon,
                msg.latitude, msg.longitude
            )
            
            if distance < self.min_distance:
                return  # Too close to last waypoint
            
            self.total_distance += distance
        
        # Record the waypoint
        waypoint = GPSWaypoint(
            lat=msg.latitude,
            lon=msg.longitude,
            alt=msg.altitude,
            accuracy=self.gps_accuracy,
            timestamp=self.get_clock().now().nanoseconds / 1e9
        )
        
        self.waypoints.append(waypoint)
        self.last_recorded_lat = msg.latitude
        self.last_recorded_lon = msg.longitude
        self.last_waypoint_time = self.get_clock().now()
        
        # Initialize reference point for coordinate transformation
        if self.reference_lat is None:
            self.reference_lat = msg.latitude
            self.reference_lon = msg.longitude
            self._init_utm_projection()
        
        # Convert to local XY coordinates
        x, y = self._latlon_to_xy(msg.latitude, msg.longitude)
        waypoint.x = x
        waypoint.y = y
        
        self.status_message = f"Recorded waypoint {len(self.waypoints)} at ({x:.2f}, {y:.2f})"
        self.get_logger().info(self.status_message)
    
    def _init_utm_projection(self):
        """Initialize UTM projection based on reference GPS position"""
        # Create a local UTM projection centered on reference point
        # This gives us accurate meter-based coordinates
        utm_zone = int((self.reference_lon + 180) / 6) + 1
        self.utm_projection = pyproj.Proj(
            proj='utm',
            zone=utm_zone,
            ellps='WGS84',
            south=(self.reference_lat < 0)
        )
        self.get_logger().info(f'Initialized UTM projection zone {utm_zone}')
    
    def _latlon_to_xy(self, lat: float, lon: float) -> Tuple[float, float]:
        """Convert lat/lon to local XY coordinates (meters)"""
        if self.utm_projection is None:
            return 0.0, 0.0
        
        # Convert to UTM
        x, y = self.utm_projection(lon, lat)
        
        # Get reference point in UTM
        ref_x, ref_y = self.utm_projection(self.reference_lon, self.reference_lat)
        
        # Return relative to reference
        return x - ref_x, y - ref_y
    
    def _haversine_distance(self, lat1: float, lon1: float, 
                           lat2: float, lon2: float) -> float:
        """Calculate distance between two GPS coordinates in meters"""
        R = 6371000  # Earth radius in meters
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_phi/2)**2 + 
             math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda/2)**2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def _calculate_polygon_area(self, points: List[Tuple[float, float]]) -> float:
        """
        Calculate polygon area using Shoelace formula.
        Points should be in local XY coordinates (meters).
        """
        if len(points) < 3:
            return 0.0
        
        area = 0.0
        n = len(points)
        
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        
        return abs(area) / 2.0
    
    def _douglas_peucker(self, points: List[GPSWaypoint], 
                         epsilon: float) -> List[GPSWaypoint]:
        """
        Simplify polygon using Douglas-Peucker algorithm.
        
        Args:
            points: List of waypoints
            epsilon: Tolerance in meters
            
        Returns:
            Simplified list of waypoints
        """
        if len(points) < 3:
            return points
        
        # Find point with maximum distance from line between first and last
        dmax = 0.0
        index = 0
        end = len(points) - 1
        
        for i in range(1, end):
            d = self._perpendicular_distance(
                points[i].x, points[i].y,
                points[0].x, points[0].y,
                points[end].x, points[end].y
            )
            if d > dmax:
                index = i
                dmax = d
        
        # If max distance is greater than epsilon, recursively simplify
        if dmax > epsilon:
            # Recursive call on both segments
            rec_results1 = self._douglas_peucker(points[:index+1], epsilon)
            rec_results2 = self._douglas_peucker(points[index:], epsilon)
            
            # Build result list
            result = rec_results1[:-1] + rec_results2
        else:
            # All points between first and last can be discarded
            result = [points[0], points[end]]
        
        return result
    
    def _perpendicular_distance(self, px: float, py: float,
                                x1: float, y1: float,
                                x2: float, y2: float) -> float:
        """Calculate perpendicular distance from point to line segment"""
        dx = x2 - x1
        dy = y2 - y1
        
        if dx == 0 and dy == 0:
            # Line segment is actually a point
            return math.sqrt((px - x1)**2 + (py - y1)**2)
        
        # Calculate perpendicular distance
        num = abs(dy * px - dx * py + x2 * y1 - y2 * x1)
        den = math.sqrt(dx**2 + dy**2)
        
        return num / den
    
    def _validate_polygon(self, points: List[Tuple[float, float]]) -> Tuple[bool, str]:
        """
        Validate polygon for self-intersections and other issues.
        
        Returns:
            (is_valid, error_message)
        """
        if len(points) < 3:
            return False, "Polygon must have at least 3 vertices"
        
        # Check for self-intersections using simple O(n^2) algorithm
        # For production, consider using a spatial index for larger polygons
        n = len(points)
        for i in range(n):
            p1 = points[i]
            p2 = points[(i + 1) % n]
            
            for j in range(i + 2, n):
                # Don't check adjacent edges
                if j == (i - 1) % n or j == (i + 1) % n:
                    continue
                
                p3 = points[j]
                p4 = points[(j + 1) % n]
                
                if self._segments_intersect(p1, p2, p3, p4):
                    return False, f"Self-intersection detected between edges {i} and {j}"
        
        return True, "Polygon is valid"
    
    def _segments_intersect(self, p1: Tuple[float, float], p2: Tuple[float, float],
                           p3: Tuple[float, float], p4: Tuple[float, float]) -> bool:
        """Check if two line segments intersect"""
        def ccw(A, B, C):
            return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])
        
        return ccw(p1,p3,p4) != ccw(p2,p3,p4) and ccw(p1,p2,p3) != ccw(p1,p2,p4)
    
    def start_recording_callback(self, request, response):
        """Handle start recording service request"""
        if self.state != self.STATE_IDLE:
            response.success = False
            response.message = "Recording already in progress"
            return response
        
        if not request.zone_name or len(request.zone_name.strip()) == 0:
            response.success = False
            response.message = "Zone name cannot be empty"
            return response
        
        # Start recording
        self.state = self.STATE_RECORDING
        self.zone_name = request.zone_name
        self.zone_priority = request.priority if request.priority > 0 else 5
        self.waypoints = []
        self.total_distance = 0.0
        self.start_time = self.get_clock().now()
        self.last_waypoint_time = self.start_time
        self.last_recorded_lat = None
        self.last_recorded_lon = None
        self.reference_lat = None
        self.reference_lon = None
        self.utm_projection = None
        
        response.success = True
        response.message = f"Started recording zone '{self.zone_name}'"
        response.start_time = self.start_time.to_msg()
        
        self.status_message = f"Recording zone '{self.zone_name}'"
        self.get_logger().info(f"Started recording zone: {self.zone_name}")
        
        return response
    
    def stop_recording_callback(self, request, response):
        """Handle stop recording service request"""
        if self.state == self.STATE_IDLE:
            response.success = False
            response.message = "No recording in progress"
            return response
        
        # Save original waypoint count
        response.original_waypoint_count = len(self.waypoints)
        
        if len(self.waypoints) < 3:
            response.success = False
            response.message = f"Insufficient waypoints ({len(self.waypoints)}). Need at least 3."
            self.state = self.STATE_IDLE
            return response
        
        # Apply simplification if requested
        simplified_waypoints = self.waypoints
        if request.simplify:
            tolerance = request.simplification_tolerance if request.simplification_tolerance > 0 else self.simplification_tol
            
            # Close polygon for simplification if requested
            if request.auto_close and len(self.waypoints) > 0:
                # Add first point at end
                first_wp = self.waypoints[0]
                last_wp = GPSWaypoint(
                    first_wp.lat, first_wp.lon, first_wp.alt,
                    first_wp.accuracy, self.get_clock().now().nanoseconds / 1e9
                )
                last_wp.x = first_wp.x
                last_wp.y = first_wp.y
                simplified_waypoints.append(last_wp)
            
            simplified_waypoints = self._douglas_peucker(simplified_waypoints, tolerance)
            self.get_logger().info(f"Simplified from {len(self.waypoints)} to {len(simplified_waypoints)} waypoints")
        
        response.final_waypoint_count = len(simplified_waypoints)
        response.total_distance = self.total_distance
        
        # Calculate area
        points_xy = [(wp.x, wp.y) for wp in simplified_waypoints]
        area = self._calculate_polygon_area(points_xy)
        response.area = area
        
        # Validate polygon
        valid, error_msg = self._validate_polygon(points_xy)
        if not valid:
            self.get_logger().warning(f"Polygon validation warning: {error_msg}")
            # Continue anyway, but log the warning
        
        # Create Zone message if saving
        if request.save_zone:
            zone = Zone()
            zone.id = self.zone_name.lower().replace(' ', '_')
            zone.name = self.zone_name
            zone.priority = self.zone_priority
            zone.enabled = True
            zone.coverage_percent = 0.0
            
            # Create polygon
            polygon = PolygonStamped()
            polygon.header = Header()
            polygon.header.frame_id = self.frame_id
            polygon.header.stamp = self.get_clock().now().to_msg()
            
            # Add vertices in local XY coordinates
            for wp in simplified_waypoints:
                point = Point32()
                point.x = wp.x
                point.y = wp.y
                point.z = 0.0  # Assume flat ground for mowing
                polygon.polygon.points.append(point)
            
            zone.polygon = polygon
            response.zone = zone
            
            # Save zone using zone_manager service
            if self.save_zone_client.wait_for_service(timeout_sec=1.0):
                save_request = SaveZone.Request()
                save_request.zone = zone
                
                future = self.save_zone_client.call_async(save_request)
                rclpy.spin_until_future_complete(self, future, timeout_sec=2.0)
                
                if future.result() is not None and future.result().success:
                    response.success = True
                    response.message = f"Zone '{self.zone_name}' saved successfully with {len(simplified_waypoints)} waypoints and area {area:.2f}m²"
                else:
                    response.success = False
                    response.message = "Failed to save zone to zone_manager"
            else:
                response.success = False
                response.message = "Zone manager service not available"
        else:
            response.success = True
            response.message = f"Recording stopped without saving"
        
        # Reset state
        self.state = self.STATE_IDLE
        self.status_message = "Ready to record"
        
        self.get_logger().info(f"Stopped recording: {response.message}")
        
        return response
    
    def control_recording_callback(self, request, response):
        """Handle control (pause/resume/cancel) service request"""
        cmd = request.command
        
        if cmd == ControlZoneRecording.Request.CMD_PAUSE:
            if self.state != self.STATE_RECORDING:
                response.success = False
                response.message = "Cannot pause: not currently recording"
                response.new_state = self.state
                return response
            
            self.state = self.STATE_PAUSED
            self.status_message = "Recording paused"
            response.success = True
            response.message = "Recording paused"
            response.new_state = self.state
            self.get_logger().info("Recording paused")
            
        elif cmd == ControlZoneRecording.Request.CMD_RESUME:
            if self.state != self.STATE_PAUSED:
                response.success = False
                response.message = "Cannot resume: not currently paused"
                response.new_state = self.state
                return response
            
            self.state = self.STATE_RECORDING
            self.status_message = f"Recording zone '{self.zone_name}'"
            response.success = True
            response.message = "Recording resumed"
            response.new_state = self.state
            self.get_logger().info("Recording resumed")
            
        elif cmd == ControlZoneRecording.Request.CMD_CANCEL:
            if self.state == self.STATE_IDLE:
                response.success = False
                response.message = "No recording to cancel"
                response.new_state = self.state
                return response
            
            waypoint_count = len(self.waypoints)
            self.state = self.STATE_IDLE
            self.waypoints = []
            self.zone_name = ""
            self.status_message = "Ready to record"
            response.success = True
            response.message = f"Recording cancelled ({waypoint_count} waypoints discarded)"
            response.new_state = self.state
            self.get_logger().info(f"Recording cancelled")
            
        else:
            response.success = False
            response.message = f"Unknown command: {cmd}"
            response.new_state = self.state
        
        return response
    
    def publish_status(self):
        """Publish current recording status"""
        # Publish detailed status
        status_msg = ZoneRecordingStatus()
        status_msg.state = self.state
        status_msg.zone_name = self.zone_name
        status_msg.waypoint_count = len(self.waypoints)
        status_msg.distance_traveled = self.total_distance
        
        # Calculate current area estimate
        if len(self.waypoints) >= 3:
            points_xy = [(wp.x, wp.y) for wp in self.waypoints]
            status_msg.estimated_area = self._calculate_polygon_area(points_xy)
        else:
            status_msg.estimated_area = 0.0
        
        status_msg.gps_quality = self.gps_quality
        status_msg.gps_accuracy = self.gps_accuracy
        
        if self.start_time:
            status_msg.start_time = self.start_time.to_msg()
        
        if self.last_waypoint_time:
            status_msg.last_waypoint_time = self.last_waypoint_time.to_msg()
        
        status_msg.visual_odometry_available = self.visual_odom_available
        status_msg.status_message = self.status_message
        
        self.status_pub.publish(status_msg)
        
        # Publish state as simple string
        state_str = String()
        if self.state == self.STATE_IDLE:
            state_str.data = "IDLE"
        elif self.state == self.STATE_RECORDING:
            state_str.data = "RECORDING"
        elif self.state == self.STATE_PAUSED:
            state_str.data = "PAUSED"
        self.state_string_pub.publish(state_str)
        
        # Publish waypoints as Path for visualization
        if len(self.waypoints) > 0:
            path_msg = Path()
            path_msg.header = Header()
            path_msg.header.frame_id = self.frame_id
            path_msg.header.stamp = self.get_clock().now().to_msg()
            
            for wp in self.waypoints:
                pose = PoseStamped()
                pose.header = path_msg.header
                pose.pose.position.x = wp.x
                pose.pose.position.y = wp.y
                pose.pose.position.z = 0.0
                pose.pose.orientation.w = 1.0
                path_msg.poses.append(pose)
            
            self.waypoints_pub.publish(path_msg)
            
            # Also publish as polygon
            polygon_msg = PolygonStamped()
            polygon_msg.header = path_msg.header
            
            for wp in self.waypoints:
                point = Point32()
                point.x = wp.x
                point.y = wp.y
                point.z = 0.0
                polygon_msg.polygon.points.append(point)
            
            self.polygon_pub.publish(polygon_msg)


def main(args=None):
    rclpy.init(args=args)
    
    try:
        node = ZoneRecorder()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
