#!/usr/bin/env python3
"""
Route Planner Node
Implements Dijkstra's algorithm for finding optimal paths through the zone graph.
Provides route planning services for multi-zone navigation.
"""

import rclpy
from rclpy.node import Node
from rosmower_msgs.msg import Route, RouteArray, ZoneGraph, ZoneGraphNode, ZoneGraphEdge
from std_srvs.srv import Trigger
from std_msgs.msg import String
import heapq
from typing import Dict, List, Optional, Tuple, Set
from collections import defaultdict
import json


class RoutePlanner(Node):
    """
    Plans optimal paths through the zone graph using Dijkstra's algorithm.
    
    Features:
    - Shortest path finding between zones
    - Multiple route consideration
    - Alternative path suggestions
    - Distance and time optimization
    """
    
    def __init__(self):
        super().__init__('route_planner')
        
        # Declare parameters
        self.declare_parameter('publish_rate', 1.0)
        
        # Graph representation
        self.graph: Dict[str, List[Tuple[str, ZoneGraphEdge]]] = defaultdict(list)
        self.zones: Dict[str, ZoneGraphNode] = {}
        self.routes: Dict[str, Route] = {}
        
        # Subscribers
        self.zone_graph_sub = self.create_subscription(
            ZoneGraph, '/zones/graph', self.zone_graph_callback, 10
        )
        self.routes_sub = self.create_subscription(
            RouteArray, '/routes/all', self.routes_callback, 10
        )
        
        # Services
        # Using simple Trigger for now - production should use custom service types
        self.plan_path_service = self.create_service(
            Trigger, '/route/plan_path', self.plan_path_callback
        )
        
        self.get_logger().info('Route Planner started')
    
    def zone_graph_callback(self, msg: ZoneGraph):
        """Update internal graph representation from zone graph"""
        # Clear existing graph
        self.graph.clear()
        self.zones.clear()
        
        # Store zones
        for node in msg.nodes:
            self.zones[node.zone_id] = node
        
        # Build adjacency list
        for edge in msg.edges:
            self.graph[edge.from_zone_id].append((edge.to_zone_id, edge))
            
            # Add reverse edge if bidirectional
            if edge.bidirectional:
                self.graph[edge.to_zone_id].append((edge.from_zone_id, edge))
        
        self.get_logger().info(
            f'Zone graph updated: {len(self.zones)} zones, {len(msg.edges)} edges'
        )
    
    def routes_callback(self, msg: RouteArray):
        """Update route database"""
        self.routes.clear()
        for route in msg.routes:
            self.routes[route.route_id] = route
        
        self.get_logger().info(f'Routes updated: {len(self.routes)} routes available')
    
    def plan_path_callback(self, request, response):
        """
        Plan shortest path between zones.
        Note: In production, create custom service with start_zone, end_zone parameters
        For now, this is a placeholder that demonstrates the algorithm
        """
        # Example usage - in production, get from request parameters
        # For now, just validate graph is ready
        
        if not self.zones:
            response.success = False
            response.message = 'Zone graph not available'
            return response
        
        if not self.graph:
            response.success = False
            response.message = 'No routes available in graph'
            return response
        
        # Example path planning
        if len(self.zones) >= 2:
            zone_ids = list(self.zones.keys())
            start = zone_ids[0]
            end = zone_ids[-1]
            
            path, distance = self.dijkstra(start, end)
            
            if path:
                response.success = True
                response.message = (
                    f'Path from {start} to {end}: '
                    f'{" -> ".join(path)} '
                    f'(distance: {distance:.1f}m)'
                )
            else:
                response.success = False
                response.message = f'No path found from {start} to {end}'
        else:
            response.success = True
            response.message = 'Graph ready but need at least 2 zones to plan path'
        
        return response
    
    def dijkstra(self, start_zone: str, end_zone: str) -> Tuple[Optional[List[str]], float]:
        """
        Dijkstra's algorithm for shortest path finding.
        
        Args:
            start_zone: Starting zone ID
            end_zone: Destination zone ID
            
        Returns:
            Tuple of (path as list of zone IDs, total distance in meters)
            Returns (None, float('inf')) if no path exists
        """
        # Validate zones exist
        if start_zone not in self.zones or end_zone not in self.zones:
            self.get_logger().error(f'Invalid zones: {start_zone} or {end_zone}')
            return None, float('inf')
        
        # Priority queue: (distance, current_zone, path)
        pq = [(0.0, start_zone, [start_zone])]
        
        # Best distances found so far
        distances: Dict[str, float] = {start_zone: 0.0}
        
        # Track visited zones
        visited: Set[str] = set()
        
        while pq:
            current_dist, current_zone, path = heapq.heappop(pq)
            
            # Found destination
            if current_zone == end_zone:
                self.get_logger().info(
                    f'Path found: {" -> ".join(path)} (distance: {current_dist:.1f}m)'
                )
                return path, current_dist
            
            # Already visited with shorter path
            if current_zone in visited:
                continue
            
            visited.add(current_zone)
            
            # Explore neighbors
            for neighbor_zone, edge in self.graph.get(current_zone, []):
                if neighbor_zone in visited:
                    continue
                
                # Calculate new distance
                new_dist = current_dist + edge.distance_meters
                
                # Update if we found a shorter path
                if neighbor_zone not in distances or new_dist < distances[neighbor_zone]:
                    distances[neighbor_zone] = new_dist
                    new_path = path + [neighbor_zone]
                    heapq.heappush(pq, (new_dist, neighbor_zone, new_path))
        
        # No path found
        self.get_logger().warn(f'No path found from {start_zone} to {end_zone}')
        return None, float('inf')
    
    def find_all_paths(self, start_zone: str, end_zone: str, 
                      max_paths: int = 3) -> List[Tuple[List[str], float]]:
        """
        Find multiple alternative paths between zones.
        Uses modified Dijkstra to find k-shortest paths.
        
        Args:
            start_zone: Starting zone ID
            end_zone: Destination zone ID
            max_paths: Maximum number of paths to find
            
        Returns:
            List of (path, distance) tuples, sorted by distance
        """
        # TODO: Implement k-shortest paths algorithm (e.g., Yen's algorithm)
        # For now, just return the single shortest path
        path, dist = self.dijkstra(start_zone, end_zone)
        if path:
            return [(path, dist)]
        return []
    
    def get_connected_zones(self, zone_id: str) -> List[str]:
        """
        Get all zones directly connected to the given zone.
        
        Args:
            zone_id: Zone to check connections for
            
        Returns:
            List of connected zone IDs
        """
        if zone_id not in self.graph:
            return []
        
        return [neighbor for neighbor, _ in self.graph[zone_id]]
    
    def is_path_exists(self, start_zone: str, end_zone: str) -> bool:
        """
        Check if a path exists between two zones without computing it.
        Uses BFS for efficiency.
        
        Args:
            start_zone: Starting zone ID
            end_zone: Destination zone ID
            
        Returns:
            True if path exists, False otherwise
        """
        if start_zone not in self.zones or end_zone not in self.zones:
            return False
        
        if start_zone == end_zone:
            return True
        
        # BFS
        visited = {start_zone}
        queue = [start_zone]
        
        while queue:
            current = queue.pop(0)
            
            for neighbor, _ in self.graph.get(current, []):
                if neighbor == end_zone:
                    return True
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
        
        return False
    
    def get_route_for_edge(self, from_zone: str, to_zone: str) -> Optional[Route]:
        """
        Get the route object for a specific edge.
        
        Args:
            from_zone: Starting zone ID
            to_zone: Destination zone ID
            
        Returns:
            Route object if found, None otherwise
        """
        for route in self.routes.values():
            if route.from_zone_id == from_zone and route.to_zone_id == to_zone:
                return route
            if route.bidirectional and route.from_zone_id == to_zone and route.to_zone_id == from_zone:
                return route
        
        return None
    
    def estimate_path_time(self, path: List[str]) -> float:
        """
        Estimate total time to traverse a path.
        
        Args:
            path: List of zone IDs forming the path
            
        Returns:
            Estimated time in seconds
        """
        total_time = 0.0
        
        for i in range(len(path) - 1):
            from_zone = path[i]
            to_zone = path[i + 1]
            
            # Find edge
            for neighbor, edge in self.graph.get(from_zone, []):
                if neighbor == to_zone:
                    total_time += edge.transit_time_seconds
                    break
        
        return total_time


def main(args=None):
    rclpy.init(args=args)
    node = RoutePlanner()
    
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
