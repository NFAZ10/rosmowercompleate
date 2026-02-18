#!/usr/bin/env python3
"""
Route Manager Node
Manages transit routes between mowing zones with GPS recording and validation.
Handles safe route storage, quality filtering, and real-time monitoring.
"""

import rclpy
from rclpy.node import Node
from rosmower_msgs.msg import Route, RouteArray, RouteRecordingStatus
from sensor_msgs.msg import NavSatFix
from nav_msgs.msg import Path
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Header, String
from std_srvs.srv import Trigger
import yaml
import os
import time
from pathlib import Path as FilePath
from typing import Dict, List, Optional, Tuple
from enum import Enum
import math
from datetime import datetime


class RecordingState(Enum):
    """Route recording state machine"""
    IDLE = 0
    RECORDING = 1
    PAUSED = 2


class RouteManager(Node):
    """
    Manages transit routes between zones with GPS-based recording.
    
    Features:
    - Real-time GPS waypoint collection with quality filtering
    - Distance and time estimation
    - Bidirectional route support
    - Route validation and storage
    - YAML persistence
    """
    
    def __init__(self):
        super().__init__('route_manager')
        
        # Declare parameters
        self.declare_parameter('routes_directory', '/ws/routes')
        self.declare_parameter('min_gps_quality_hdop', 2.0)
        self.declare_parameter('waypoint_spacing_meters', 1.0)
        self.declare_parameter('max_recording_time_seconds', 600)
        self.declare_parameter('publish_rate', 1.0)
        self.declare_parameter('frame_id', 'map')
        
        # Get parameters
        self.routes_dir = FilePath(self.get_parameter('routes_directory').value)
        self.min_gps_quality = self.get_parameter('min_gps_quality_hdop').value
        self.waypoint_spacing = self.get_parameter('waypoint_spacing_meters').value
        self.max_recording_time = self.get_parameter('max_recording_time_seconds').value
        self.publish_rate = self.get_parameter('publish_rate').value
        self.frame_id = self.get_parameter('frame_id').value
        
        # Create routes directory
        self.routes_dir.mkdir(parents=True, exist_ok=True)
        
        # Recording state
        self.state = RecordingState.IDLE
        self.current_route: Optional[Route] = None
        self.recording_start_time: float = 0.0
        self.last_waypoint: Optional[NavSatFix] = None
        self.current_gps: Optional[NavSatFix] = None
        self.current_gps_quality: float = 99.0  # HDOP
        
        # In-memory route storage
        self.routes: Dict[str, Route] = {}
        
        # Publishers
        self.status_pub = self.create_publisher(
            RouteRecordingStatus, '/route/recording/status', 10
        )
        self.path_pub = self.create_publisher(
            Path, '/route/recording/path', 10
        )
        self.routes_pub = self.create_publisher(
            RouteArray, '/routes/all', 10
        )
        self.active_route_pub = self.create_publisher(
            Route, '/route/active', 10
        )
        
        # Subscribers
        self.gps_sub = self.create_subscription(
            NavSatFix, '/gps/fix', self.gps_callback, 10
        )
        
        # Services - Using simple Trigger service for now
        # TODO: Create custom service types for better parameter passing
        self.start_service = self.create_service(
            Trigger, '/route/record/start', self.start_recording_callback
        )
        self.stop_service = self.create_service(
            Trigger, '/route/record/stop', self.stop_recording_callback
        )
        self.pause_service = self.create_service(
            Trigger, '/route/record/pause', self.pause_recording_callback
        )
        self.resume_service = self.create_service(
            Trigger, '/route/record/resume', self.resume_recording_callback
        )
        self.cancel_service = self.create_service(
            Trigger, '/route/record/cancel', self.cancel_recording_callback
        )
        
        # Timers
        self.create_timer(1.0 / self.publish_rate, self.publish_status)
        self.create_timer(0.5, self.publish_path)  # 2 Hz during recording
        
        # Load existing routes
        self.load_all_routes()
        
        self.get_logger().info('Route Manager started')
        self.get_logger().info(f'Routes directory: {self.routes_dir}')
        self.get_logger().info(f'Loaded {len(self.routes)} route(s)')
        self.get_logger().info(f'GPS quality threshold: HDOP < {self.min_gps_quality}')
        self.get_logger().info(f'Waypoint spacing: {self.waypoint_spacing}m')
    
    def load_all_routes(self):
        """Load all route files from the routes directory"""
        yaml_files = list(self.routes_dir.glob('*.yaml')) + list(self.routes_dir.glob('*.yml'))
        
        for file_path in yaml_files:
            try:
                route = self._load_route_from_file(file_path)
                if route:
                    self.routes[route.route_id] = route
                    self.get_logger().info(
                        f'Loaded route: {route.route_name} ({route.route_id})'
                    )
            except Exception as e:
                self.get_logger().error(f'Failed to load route from {file_path}: {e}')
        
        # Publish all routes
        self.publish_all_routes()
    
    def _load_route_from_file(self, file_path: FilePath) -> Optional[Route]:
        """Load a route from a YAML file"""
        try:
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)
            
            route = Route()
            route.header.stamp = self.get_clock().now().to_msg()
            route.header.frame_id = self.frame_id
            
            route.route_id = data.get('route_id', file_path.stem)
            route.route_name = data.get('route_name', route.route_id)
            route.from_zone_id = data.get('from_zone_id', '')
            route.to_zone_id = data.get('to_zone_id', '')
            route.route_type = data.get('route_type', 'UNKNOWN')
            route.bidirectional = data.get('bidirectional', True)
            route.max_speed_mps = float(data.get('max_speed_mps', 0.5))
            route.path_width_meters = float(data.get('path_width_meters', 2.0))
            route.mow_during_transit = data.get('mow_during_transit', False)
            route.total_distance_meters = float(data.get('total_distance_meters', 0.0))
            route.estimated_transit_time_seconds = float(
                data.get('estimated_transit_time_seconds', 0.0)
            )
            route.tags = data.get('tags', [])
            
            # Load waypoints
            waypoints_data = data.get('waypoints', [])
            for wp_data in waypoints_data:
                wp = NavSatFix()
                wp.latitude = float(wp_data['latitude'])
                wp.longitude = float(wp_data['longitude'])
                wp.altitude = float(wp_data.get('altitude', 0.0))
                route.waypoints.append(wp)
            
            return route
            
        except Exception as e:
            self.get_logger().error(f'Error loading route from {file_path}: {e}')
            return None
    
    def gps_callback(self, msg: NavSatFix):
        """Handle GPS updates"""
        self.current_gps = msg
        
        # Extract GPS quality (HDOP from position_covariance if available)
        if msg.position_covariance[0] > 0:
            # Estimate HDOP from covariance
            self.current_gps_quality = math.sqrt(msg.position_covariance[0])
        else:
            self.current_gps_quality = 99.0  # Unknown quality
        
        # Add waypoint if recording
        if self.state == RecordingState.RECORDING and self.current_route:
            self._try_add_waypoint(msg)
    
    def _try_add_waypoint(self, gps: NavSatFix):
        """Try to add a waypoint if it meets quality and spacing criteria"""
        # Check GPS quality
        if self.current_gps_quality > self.min_gps_quality:
            self.get_logger().warn(
                f'GPS quality poor (HDOP={self.current_gps_quality:.2f}), '
                f'skipping waypoint',
                throttle_duration_sec=5.0
            )
            return
        
        # Check spacing from last waypoint
        if self.last_waypoint:
            distance = self._calculate_distance(
                self.last_waypoint.latitude, self.last_waypoint.longitude,
                gps.latitude, gps.longitude
            )
            if distance < self.waypoint_spacing:
                return  # Too close to last waypoint
        
        # Add waypoint
        self.current_route.waypoints.append(gps)
        self.last_waypoint = gps
        
        # Update distance
        if len(self.current_route.waypoints) >= 2:
            last_wp = self.current_route.waypoints[-2]
            dist = self._calculate_distance(
                last_wp.latitude, last_wp.longitude,
                gps.latitude, gps.longitude
            )
            self.current_route.total_distance_meters += dist
        
        self.get_logger().info(
            f'Waypoint added: {len(self.current_route.waypoints)} total, '
            f'{self.current_route.total_distance_meters:.1f}m',
            throttle_duration_sec=2.0
        )
    
    def _calculate_distance(self, lat1: float, lon1: float, 
                           lat2: float, lon2: float) -> float:
        """Calculate distance between two GPS coordinates using Haversine formula"""
        R = 6371000  # Earth radius in meters
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) *
             math.sin(delta_lambda / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def start_recording_callback(self, request, response):
        """Start route recording - controlled via web API with parameters"""
        if self.state != RecordingState.IDLE:
            response.success = False
            response.message = f'Already {self.state.name}'
            return response
        
        if not self.current_gps:
            response.success = False
            response.message = 'No GPS signal available'
            return response
        
        # Create new route (parameters set via web API)
        self.current_route = Route()
        self.current_route.header.stamp = self.get_clock().now().to_msg()
        self.current_route.header.frame_id = self.frame_id
        
        # Generate route ID with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.current_route.route_id = f'route_{timestamp}'
        self.current_route.route_name = self.current_route.route_id
        
        # Default values (to be updated via parameters in production)
        self.current_route.bidirectional = True
        self.current_route.max_speed_mps = 0.5
        self.current_route.path_width_meters = 2.0
        self.current_route.mow_during_transit = False
        
        self.state = RecordingState.RECORDING
        self.recording_start_time = time.time()
        self.last_waypoint = None
        
        self.get_logger().info(
            f'Started recording route: {self.current_route.route_id}'
        )
        
        response.success = True
        response.message = f'Recording started: {self.current_route.route_id}'
        return response
    
    def stop_recording_callback(self, request, response):
        """Stop route recording and save"""
        if self.state not in [RecordingState.RECORDING, RecordingState.PAUSED]:
            response.success = False
            response.message = 'Not recording'
            return response
        
        if not self.current_route or len(self.current_route.waypoints) < 2:
            response.success = False
            response.message = 'Insufficient waypoints (need at least 2)'
            return response
        
        # Finalize route
        duration = time.time() - self.recording_start_time
        self.current_route.estimated_transit_time_seconds = duration
        self.current_route.created_at = self.get_clock().now().to_msg()
        
        # Calculate average speed if we have distance and time
        if self.current_route.total_distance_meters > 0 and duration > 0:
            avg_speed = self.current_route.total_distance_meters / duration
            # Use conservative speed for autonomous transit
            self.current_route.max_speed_mps = min(avg_speed * 0.7, 0.5)
        
        # Save route
        try:
            file_path = self._save_route(self.current_route)
            self.routes[self.current_route.route_id] = self.current_route
            
            self.get_logger().info(
                f'Route saved: {self.current_route.route_name} '
                f'({len(self.current_route.waypoints)} waypoints, '
                f'{self.current_route.total_distance_meters:.1f}m)'
            )
            
            # Publish updated route list
            self.publish_all_routes()
            
            response.success = True
            response.message = f'Route saved to {file_path}'
            
        except Exception as e:
            self.get_logger().error(f'Failed to save route: {e}')
            response.success = False
            response.message = f'Save failed: {e}'
        
        # Reset state
        self.state = RecordingState.IDLE
        self.current_route = None
        self.last_waypoint = None
        
        return response
    
    def pause_recording_callback(self, request, response):
        """Pause route recording"""
        if self.state != RecordingState.RECORDING:
            response.success = False
            response.message = f'Cannot pause from {self.state.name}'
            return response
        
        self.state = RecordingState.PAUSED
        self.get_logger().info('Route recording paused')
        
        response.success = True
        response.message = 'Recording paused'
        return response
    
    def resume_recording_callback(self, request, response):
        """Resume route recording"""
        if self.state != RecordingState.PAUSED:
            response.success = False
            response.message = f'Cannot resume from {self.state.name}'
            return response
        
        self.state = RecordingState.RECORDING
        self.get_logger().info('Route recording resumed')
        
        response.success = True
        response.message = 'Recording resumed'
        return response
    
    def cancel_recording_callback(self, request, response):
        """Cancel route recording without saving"""
        if self.state == RecordingState.IDLE:
            response.success = False
            response.message = 'Not recording'
            return response
        
        route_id = self.current_route.route_id if self.current_route else 'unknown'
        
        self.state = RecordingState.IDLE
        self.current_route = None
        self.last_waypoint = None
        
        self.get_logger().info(f'Route recording cancelled: {route_id}')
        
        response.success = True
        response.message = f'Recording cancelled: {route_id}'
        return response
    
    def _save_route(self, route: Route) -> str:
        """Save route to YAML file"""
        # Create filename
        if route.from_zone_id and route.to_zone_id:
            filename = f'{route.from_zone_id}_to_{route.to_zone_id}_{int(time.time())}.yaml'
        else:
            filename = f'{route.route_id}.yaml'
        
        file_path = self.routes_dir / filename
        
        # Convert to dictionary
        route_dict = {
            'route_id': route.route_id,
            'route_name': route.route_name,
            'from_zone_id': route.from_zone_id,
            'to_zone_id': route.to_zone_id,
            'route_type': route.route_type,
            'bidirectional': route.bidirectional,
            'max_speed_mps': float(route.max_speed_mps),
            'path_width_meters': float(route.path_width_meters),
            'mow_during_transit': route.mow_during_transit,
            'total_distance_meters': float(route.total_distance_meters),
            'estimated_transit_time_seconds': float(route.estimated_transit_time_seconds),
            'tags': list(route.tags),
            'created_at': datetime.now().isoformat(),
            'waypoints': [
                {
                    'latitude': float(wp.latitude),
                    'longitude': float(wp.longitude),
                    'altitude': float(wp.altitude)
                }
                for wp in route.waypoints
            ]
        }
        
        # Write YAML
        with open(file_path, 'w') as f:
            yaml.safe_dump(route_dict, f, default_flow_style=False, sort_keys=False)
        
        return str(file_path)
    
    def publish_status(self):
        """Publish current recording status"""
        status = RouteRecordingStatus()
        status.header.stamp = self.get_clock().now().to_msg()
        status.header.frame_id = self.frame_id
        
        status.is_recording = (self.state == RecordingState.RECORDING)
        status.is_paused = (self.state == RecordingState.PAUSED)
        
        if self.current_route:
            status.current_route_id = self.current_route.route_id
            status.from_zone_id = self.current_route.from_zone_id
            status.to_zone_id = self.current_route.to_zone_id
            status.waypoints_collected = len(self.current_route.waypoints)
            status.distance_so_far_meters = self.current_route.total_distance_meters
            status.recording_duration_seconds = time.time() - self.recording_start_time
        
        if self.current_gps:
            status.current_gps_lat = self.current_gps.latitude
            status.current_gps_lon = self.current_gps.longitude
            status.current_gps_quality = self.current_gps_quality
        
        self.status_pub.publish(status)
    
    def publish_path(self):
        """Publish current recording path for visualization"""
        if self.state == RecordingState.IDLE or not self.current_route:
            return
        
        if len(self.current_route.waypoints) == 0:
            return
        
        path = Path()
        path.header.stamp = self.get_clock().now().to_msg()
        path.header.frame_id = self.frame_id
        
        for wp in self.current_route.waypoints:
            pose = PoseStamped()
            pose.header = path.header
            pose.pose.position.x = wp.longitude  # Note: simplified, needs proper transform
            pose.pose.position.y = wp.latitude
            pose.pose.position.z = wp.altitude
            path.poses.append(pose)
        
        self.path_pub.publish(path)
    
    def publish_all_routes(self):
        """Publish all available routes"""
        route_array = RouteArray()
        route_array.header.stamp = self.get_clock().now().to_msg()
        route_array.header.frame_id = self.frame_id
        
        for route in self.routes.values():
            route_array.routes.append(route)
        
        self.routes_pub.publish(route_array)
        
        self.get_logger().info(
            f'Published {len(self.routes)} routes',
            throttle_duration_sec=10.0
        )


def main(args=None):
    rclpy.init(args=args)
    node = RouteManager()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
