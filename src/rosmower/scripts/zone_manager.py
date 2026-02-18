#!/usr/bin/env python3
"""
Zone Manager Node
Manages mowing zones with persistent storage, validation, and ROS2 services
"""

import rclpy
from rclpy.node import Node
from rosmower_msgs.msg import Zone, ZoneArray, ZoneGraph, ZoneGraphNode, ZoneGraphEdge, Route, RouteArray
from rosmower_msgs.srv import SaveZone, LoadZone, ListZones, DeleteZone
from geometry_msgs.msg import PolygonStamped, Point32
from std_msgs.msg import Header
import json
import os
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import time
import math


class ZoneManager(Node):
    def __init__(self):
        super().__init__('zone_manager')
        
        # Declare parameters
        self.declare_parameter('zones_directory', '/ws/zones')
        self.declare_parameter('routes_directory', '/ws/routes')
        self.declare_parameter('publish_rate', 1.0)  # Hz
        self.declare_parameter('frame_id', 'map')
        
        # Get parameters
        self.zones_dir = Path(self.get_parameter('zones_directory').value)
        self.routes_dir = Path(self.get_parameter('routes_directory').value)
        self.publish_rate = self.get_parameter('publish_rate').value
        self.frame_id = self.get_parameter('frame_id').value
        
        # Create zones directory if it doesn't exist
        self.zones_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory zone storage
        self.zones: Dict[str, Zone] = {}
        self.current_zone_id: Optional[str] = None
        
        # Route storage for graph generation
        self.routes: Dict[str, Route] = {}
        
        # Zone metadata (priority, last_mowed, etc.)
        self.zone_metadata: Dict[str, dict] = {}
        
        # Publishers
        self.zones_pub = self.create_publisher(ZoneArray, '/zones', 10)
        self.current_zone_pub = self.create_publisher(Zone, '/zone/current', 10)
        self.zone_graph_pub = self.create_publisher(ZoneGraph, '/zones/graph', 10)
        
        # Services
        self.save_service = self.create_service(
            SaveZone, '/zone/save', self.save_zone_callback
        )
        self.load_service = self.create_service(
            LoadZone, '/zone/load', self.load_zone_callback
        )
        self.list_service = self.create_service(
            ListZones, '/zone/list', self.list_zones_callback
        )
        self.delete_service = self.create_service(
            DeleteZone, '/zone/delete', self.delete_zone_callback
        )
        
        # Subscribe to routes for graph generation
        self.routes_sub = self.create_subscription(
            RouteArray, '/routes/all', self.routes_callback, 10
        )
        
        # Timer for periodic publishing
        self.create_timer(1.0 / self.publish_rate, self.publish_zones)
        
        # Load all zones from disk on startup
        self.load_all_zones()
        
        self.get_logger().info(f'Zone Manager started')
        self.get_logger().info(f'Zones directory: {self.zones_dir}')
        self.get_logger().info(f'Loaded {len(self.zones)} zone(s)')
        
    def load_all_zones(self):
        """Load all zone files from the zones directory"""
        yaml_files = list(self.zones_dir.glob('*.yaml')) + list(self.zones_dir.glob('*.yml'))
        json_files = list(self.zones_dir.glob('*.json'))
        
        for file_path in yaml_files + json_files:
            try:
                zone = self._load_zone_from_file(file_path)
                if zone:
                    self.zones[zone.id] = zone
                    self.get_logger().info(f'Loaded zone: {zone.name} ({zone.id})')
            except Exception as e:
                self.get_logger().error(f'Failed to load zone from {file_path}: {e}')
    
    def _load_zone_from_file(self, file_path: Path) -> Optional[Zone]:
        """Load a zone from a YAML or JSON file"""
        try:
            with open(file_path, 'r') as f:
                if file_path.suffix in ['.yaml', '.yml']:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            
            # Create Zone message
            zone = Zone()
            zone.id = data.get('id', file_path.stem)
            zone.name = data.get('name', zone.id)
            zone.priority = data.get('priority', 5)
            zone.enabled = data.get('enabled', True)
            zone.coverage_percent = data.get('coverage_percent', 0.0)
            
            # Create polygon
            polygon = PolygonStamped()
            polygon.header = Header()
            polygon.header.frame_id = data.get('frame_id', self.frame_id)
            polygon.header.stamp = self.get_clock().now().to_msg()
            
            # Add vertices
            vertices = data.get('vertices', [])
            for vertex in vertices:
                point = Point32()
                point.x = float(vertex.get('x', 0.0))
                point.y = float(vertex.get('y', 0.0))
                point.z = float(vertex.get('z', 0.0))
                polygon.polygon.points.append(point)
            
            zone.polygon = polygon
            
            return zone
            
        except Exception as e:
            self.get_logger().error(f'Error loading zone from {file_path}: {e}')
            return None
    
    def _save_zone_to_file(self, zone: Zone) -> bool:
        """Save a zone to a YAML file"""
        try:
            file_path = self.zones_dir / f'{zone.id}.yaml'
            
            # Convert zone to dictionary
            data = {
                'id': zone.id,
                'name': zone.name,
                'priority': zone.priority,
                'enabled': zone.enabled,
                'coverage_percent': zone.coverage_percent,
                'frame_id': zone.polygon.header.frame_id,
                'vertices': [
                    {'x': float(p.x), 'y': float(p.y), 'z': float(p.z)}
                    for p in zone.polygon.polygon.points
                ]
            }
            
            # Write to file
            with open(file_path, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)
            
            self.get_logger().info(f'Saved zone {zone.name} to {file_path}')
            return True
            
        except Exception as e:
            self.get_logger().error(f'Failed to save zone {zone.id}: {e}')
            return False
    
    def _validate_zone(self, zone: Zone) -> tuple[bool, str]:
        """Validate a zone definition"""
        # Check ID
        if not zone.id or len(zone.id.strip()) == 0:
            return False, "Zone ID cannot be empty"
        
        # Check name
        if not zone.name or len(zone.name.strip()) == 0:
            return False, "Zone name cannot be empty"
        
        # Check polygon has at least 3 vertices
        if len(zone.polygon.polygon.points) < 3:
            return False, "Zone must have at least 3 vertices"
        
        # Check for duplicate consecutive vertices
        points = zone.polygon.polygon.points
        for i in range(len(points)):
            p1 = points[i]
            p2 = points[(i + 1) % len(points)]
            if abs(p1.x - p2.x) < 0.01 and abs(p1.y - p2.y) < 0.01:
                return False, f"Duplicate consecutive vertices at index {i}"
        
        # Priority range check
        if zone.priority > 255:
            return False, "Priority must be 0-255"
        
        return True, "Zone is valid"
    
    def save_zone_callback(self, request, response):
        """Handle SaveZone service request"""
        zone = request.zone
        
        # Validate zone
        valid, message = self._validate_zone(zone)
        if not valid:
            response.success = False
            response.message = f"Validation failed: {message}"
            self.get_logger().error(f'Zone validation failed: {message}')
            return response
        
        # Save to disk
        if self._save_zone_to_file(zone):
            # Update in-memory storage
            self.zones[zone.id] = zone
            response.success = True
            response.message = f"Zone '{zone.name}' saved successfully"
            self.get_logger().info(f'Zone saved: {zone.name} ({zone.id})')
        else:
            response.success = False
            response.message = "Failed to save zone to disk"
        
        return response
    
    def load_zone_callback(self, request, response):
        """Handle LoadZone service request"""
        zone_id = request.zone_id
        
        # Check if zone exists in memory
        if zone_id in self.zones:
            response.success = True
            response.zone = self.zones[zone_id]
            self.current_zone_id = zone_id
            self.get_logger().info(f'Loaded zone: {response.zone.name} ({zone_id})')
        else:
            # Try to load from disk
            file_paths = [
                self.zones_dir / f'{zone_id}.yaml',
                self.zones_dir / f'{zone_id}.yml',
                self.zones_dir / f'{zone_id}.json'
            ]
            
            loaded = False
            for file_path in file_paths:
                if file_path.exists():
                    zone = self._load_zone_from_file(file_path)
                    if zone:
                        self.zones[zone_id] = zone
                        response.success = True
                        response.zone = zone
                        self.current_zone_id = zone_id
                        loaded = True
                        self.get_logger().info(f'Loaded zone from disk: {zone.name}')
                        break
            
            if not loaded:
                response.success = False
                self.get_logger().warning(f'Zone not found: {zone_id}')
        
        return response
    
    def list_zones_callback(self, request, response):
        """Handle ListZones service request"""
        # Create ZoneArray message
        zone_array = ZoneArray()
        zone_array.header = Header()
        zone_array.header.stamp = self.get_clock().now().to_msg()
        zone_array.header.frame_id = self.frame_id
        
        # Add all zones
        for zone_id, zone in self.zones.items():
            zone_array.zones.append(zone)
            response.zone_ids.append(zone_id)
        
        response.zones = zone_array
        
        self.get_logger().info(f'Listed {len(self.zones)} zone(s)')
        return response
    
    def delete_zone_callback(self, request, response):
        """Handle DeleteZone service request"""
        zone_id = request.zone_id
        
        # Check if zone exists
        if zone_id not in self.zones:
            response.success = False
            response.message = f"Zone '{zone_id}' not found"
            self.get_logger().warning(f'Cannot delete zone {zone_id}: not found')
            return response
        
        # Remove from memory
        zone_name = self.zones[zone_id].name
        del self.zones[zone_id]
        
        # Remove from disk
        file_paths = [
            self.zones_dir / f'{zone_id}.yaml',
            self.zones_dir / f'{zone_id}.yml',
            self.zones_dir / f'{zone_id}.json'
        ]
        
        deleted = False
        for file_path in file_paths:
            if file_path.exists():
                try:
                    file_path.unlink()
                    deleted = True
                    self.get_logger().info(f'Deleted zone file: {file_path}')
                except Exception as e:
                    self.get_logger().error(f'Failed to delete {file_path}: {e}')
        
        # Clear current zone if it was deleted
        if self.current_zone_id == zone_id:
            self.current_zone_id = None
        
        response.success = True
        response.message = f"Zone '{zone_name}' deleted successfully"
        self.get_logger().info(f'Zone deleted: {zone_name} ({zone_id})')
        
        return response
    
    def publish_zones(self):
        """Periodically publish all zones and current zone"""
        # Publish all zones
        zone_array = ZoneArray()
        zone_array.header = Header()
        zone_array.header.stamp = self.get_clock().now().to_msg()
        zone_array.header.frame_id = self.frame_id
        
        for zone in self.zones.values():
            zone_array.zones.append(zone)
        
        self.zones_pub.publish(zone_array)
        
        # Publish current zone if one is selected
        if self.current_zone_id and self.current_zone_id in self.zones:
            self.current_zone_pub.publish(self.zones[self.current_zone_id])
        
        # Publish zone graph
        self.publish_zone_graph()
    
    def routes_callback(self, msg: RouteArray):
        """Update route storage and regenerate graph when routes change"""
        self.routes.clear()
        for route in msg.routes:
            self.routes[route.route_id] = route
        
        self.get_logger().info(
            f'Routes updated: {len(self.routes)} routes',
            throttle_duration_sec=5.0
        )
        
        # Regenerate zone graph
        self.publish_zone_graph()
    
    def calculate_zone_center(self, zone: Zone) -> Tuple[float, float]:
        """
        Calculate the center point of a zone from its vertices.
        Returns (latitude, longitude) or (0, 0) if cannot calculate.
        """
        if len(zone.polygon.polygon.points) == 0:
            return 0.0, 0.0
        
        # Calculate centroid
        sum_x = sum(p.x for p in zone.polygon.polygon.points)
        sum_y = sum(p.y for p in zone.polygon.polygon.points)
        count = len(zone.polygon.polygon.points)
        
        center_x = sum_x / count
        center_y = sum_y / count
        
        return center_y, center_x  # lat, lon
    
    def generate_zone_graph(self) -> ZoneGraph:
        """
        Generate zone connectivity graph from available routes.
        Returns a ZoneGraph message with nodes and edges.
        """
        graph = ZoneGraph()
        graph.header.stamp = self.get_clock().now().to_msg()
        graph.header.frame_id = self.frame_id
        
        # Create nodes for each zone
        for zone_id, zone in self.zones.items():
            node = ZoneGraphNode()
            node.zone_id = zone_id
            node.zone_name = zone.name
            
            # Calculate center
            lat, lon = self.calculate_zone_center(zone)
            node.center_lat = lat
            node.center_lon = lon
            
            # Get metadata
            metadata = self.zone_metadata.get(zone_id, {})
            node.priority = metadata.get('priority', zone.priority)
            node.estimated_mow_time_seconds = metadata.get('estimated_time', 300.0)
            
            graph.nodes.append(node)
        
        # Create edges from routes
        for route_id, route in self.routes.items():
            if not route.from_zone_id or not route.to_zone_id:
                continue
            
            # Check if both zones exist
            if route.from_zone_id not in self.zones or route.to_zone_id not in self.zones:
                self.get_logger().warn(
                    f'Route {route_id} references non-existent zones',
                    throttle_duration_sec=10.0
                )
                continue
            
            edge = ZoneGraphEdge()
            edge.from_zone_id = route.from_zone_id
            edge.to_zone_id = route.to_zone_id
            edge.route_id = route_id
            edge.distance_meters = route.total_distance_meters
            edge.transit_time_seconds = route.estimated_transit_time_seconds
            edge.bidirectional = route.bidirectional
            
            graph.edges.append(edge)
        
        return graph
    
    def publish_zone_graph(self):
        """Generate and publish zone connectivity graph"""
        graph = self.generate_zone_graph()
        self.zone_graph_pub.publish(graph)
        
        self.get_logger().info(
            f'Zone graph published: {len(graph.nodes)} nodes, {len(graph.edges)} edges',
            throttle_duration_sec=10.0
        )
    
    def get_connected_zones(self, zone_id: str) -> List[str]:
        """
        Get list of zones directly connected to the given zone via routes.
        
        Args:
            zone_id: Zone ID to check
            
        Returns:
            List of connected zone IDs
        """
        connected = []
        
        for route in self.routes.values():
            if route.from_zone_id == zone_id:
                connected.append(route.to_zone_id)
            elif route.bidirectional and route.to_zone_id == zone_id:
                connected.append(route.from_zone_id)
        
        return list(set(connected))  # Remove duplicates
    
    def update_zone_priority(self, zone_id: str, priority: int) -> bool:
        """
        Update mowing priority for a zone.
        
        Args:
            zone_id: Zone ID to update
            priority: New priority (0-255, lower = higher priority)
            
        Returns:
            True if successful, False otherwise
        """
        if zone_id not in self.zones:
            return False
        
        if priority < 0 or priority > 255:
            return False
        
        # Update zone
        self.zones[zone_id].priority = priority
        
        # Update metadata
        if zone_id not in self.zone_metadata:
            self.zone_metadata[zone_id] = {}
        self.zone_metadata[zone_id]['priority'] = priority
        
        # Save to disk
        self._save_zone_to_file(self.zones[zone_id])
        
        # Regenerate graph
        self.publish_zone_graph()
        
        return True
    
    def update_zone_metadata(self, zone_id: str, metadata: dict) -> bool:
        """
        Update metadata for a zone (priority, last_mowed, estimated_time, etc.).
        
        Args:
            zone_id: Zone ID to update
            metadata: Dictionary with metadata fields
            
        Returns:
            True if successful, False otherwise
        """
        if zone_id not in self.zones:
            return False
        
        # Update or create metadata
        if zone_id not in self.zone_metadata:
            self.zone_metadata[zone_id] = {}
        
        self.zone_metadata[zone_id].update(metadata)
        
        # Update priority in zone if provided
        if 'priority' in metadata:
            self.zones[zone_id].priority = metadata['priority']
            self._save_zone_to_file(self.zones[zone_id])
        
        # Regenerate graph
        self.publish_zone_graph()
        
        return True


def main(args=None):
    rclpy.init(args=args)
    node = ZoneManager()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
