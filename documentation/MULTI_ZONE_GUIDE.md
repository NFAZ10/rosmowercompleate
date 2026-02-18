# Multi-Zone Management System - Complete Guide

## System Overview

The Multi-Zone Management System enables your autonomous mower to operate across multiple discrete mowing zones with safe, recorded transit routes between them. This is essential for properties with separated lawns (front yard, back yard, side yards) or zones divided by obstacles (buildings, driveways, fences).

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Multi-Zone System                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐      ┌──────────────┐                   │
│  │ Zone Manager │◄────►│Route Manager │                   │
│  │              │      │              │                   │
│  │ - Zone CRUD  │      │ - Record GPS │                   │
│  │ - Metadata   │      │ - Quality    │                   │
│  │ - Graph Gen  │      │ - Storage    │                   │
│  └──────┬───────┘      └──────┬───────┘                   │
│         │                     │                            │
│         │   ┌─────────────────┘                            │
│         │   │                                              │
│         ▼   ▼                                              │
│  ┌──────────────┐       ┌──────────────┐                  │
│  │ Zone Graph   │──────►│Route Planner │                  │
│  │              │       │              │                  │
│  │ - Nodes      │       │ - Dijkstra   │                  │
│  │ - Edges      │       │ - Path Find  │                  │
│  └──────────────┘       └──────────────┘                  │
│         │                     │                            │
│         └──────────┬──────────┘                            │
│                    ▼                                       │
│            ┌──────────────┐                                │
│            │  Web UI      │                                │
│            │              │                                │
│            │ - Zone List  │                                │
│            │ - Route Rec  │                                │
│            │ - Graph Viz  │                                │
│            └──────────────┘                                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. **Zone Manager** (`zone_manager.py`)
- Manages mowing zone definitions
- Generates zone connectivity graph
- Publishes `/zones/graph` topic
- Enhanced with priority and metadata management

### 2. **Route Manager** (`route_manager.py`)
- Records GPS waypoints during walking
- Filters by GPS quality (HDOP < 2.0)
- Enforces waypoint spacing (1m default)
- Stores routes as YAML files
- Publishes recording status and path visualization

### 3. **Route Planner** (`route_planner.py`)
- Implements Dijkstra's shortest path algorithm
- Finds optimal routes through zone graph
- Supports multiple path queries
- Future: Battery-aware planning

### 4. **Web Interface** (`zone_routes.html`)
- Zone list with priority management
- Route recording controls
- Live GPS quality monitoring
- Zone connectivity graph visualization
- Route management (view, delete)

## ROS2 Topics

### Published
- `/zones` - ZoneArray (all defined zones)
- `/zones/graph` - ZoneGraph (connectivity graph)
- `/routes/all` - RouteArray (all recorded routes)
- `/route/recording/status` - RouteRecordingStatus (live recording stats)
- `/route/recording/path` - Path (visualization during recording)
- `/route/active` - Route (currently selected route)

### Subscribed
- `/gps/fix` - NavSatFix (GPS position for recording)

## ROS2 Services

- `/route/record/start` - Start route recording
- `/route/record/stop` - Stop and save route
- `/route/record/pause` - Pause recording
- `/route/record/resume` - Resume recording
- `/route/record/cancel` - Cancel without saving
- `/route/plan_path` - Plan shortest path between zones

## Message Types

### Route.msg
Complete route definition with:
- Zone endpoints (from/to)
- Route type (DRIVEWAY, GATE_PASSAGE, etc.)
- Waypoints (GPS coordinates)
- Speed limits and path width
- Bidirectional flag
- Tags for categorization

### ZoneGraph.msg
Graph representation with:
- Nodes (zones with metadata)
- Edges (routes connecting zones)

### RouteRecordingStatus.msg
Real-time recording status:
- Recording/paused state
- Waypoint count
- Distance traveled
- GPS quality

## Use Cases

### 1. **Separated Property Sections**
- **Scenario**: Front yard and back yard separated by house
- **Solution**: Record driveway route connecting them
- **Benefit**: Autonomous transit without manual intervention

### 2. **Multiple Buildings**
- **Scenario**: Property with main house and garage with separate lawn areas
- **Solution**: Record "around building" routes
- **Benefit**: Complete coverage with safe navigation

### 3. **Gated Areas**
- **Scenario**: Side yard behind a gate
- **Solution**: Record gate passage route (with future AprilTag integration)
- **Benefit**: Automated gate detection and traversal

### 4. **Priority Zones**
- **Scenario**: Front yard (high visibility) needs more frequent mowing
- **Solution**: Set priority in zone metadata
- **Benefit**: Intelligent scheduling based on importance

## Storage Format

### Zones Directory (`/ws/zones/`)
```yaml
id: backyard
name: "Back Yard"
priority: 5
enabled: true
coverage_percent: 0.0
frame_id: map
vertices:
  - {x: 0.0, y: 0.0, z: 0.0}
  - {x: 10.0, y: 0.0, z: 0.0}
  - {x: 10.0, y: 10.0, z: 0.0}
  - {x: 0.0, y: 10.0, z: 0.0}
```

### Routes Directory (`/ws/routes/`)
```yaml
route_id: "route_backyard_to_frontyard_20240115"
route_name: "Main Driveway"
from_zone_id: "backyard"
to_zone_id: "frontyard"
route_type: "DRIVEWAY"
bidirectional: true
max_speed_mps: 0.5
path_width_meters: 2.5
mow_during_transit: false
tags: ["paved", "main", "wide"]
created_at: "2024-01-15T10:30:00Z"
waypoints:
  - latitude: 37.12345
    longitude: -122.12345
    altitude: 10.5
  - latitude: 37.12346
    longitude: -122.12346
    altitude: 10.6
total_distance_meters: 25.3
estimated_transit_time_seconds: 50.6
```

## Workflow

### Initial Setup
1. Start the web server: `./start-web-server.sh`
2. Launch zone/route management: `ros2 launch rosmower zone_and_route_management.launch.py`
3. Open web interface: `http://<robot-ip>:8080/routes`

### Recording a Route
1. Navigate to Route Manager page
2. Select from_zone and to_zone
3. Configure route parameters (type, speed, width)
4. Wait for good GPS quality (green indicator)
5. Click "Start Recording"
6. Walk slowly along desired path (0.5 m/s)
7. Watch waypoint count increase
8. Click "Stop & Save" when complete
9. Route automatically saved and added to graph

### Planning a Multi-Zone Mission
1. Use route planner to find shortest path
2. System uses Dijkstra's algorithm on zone graph
3. Returns ordered list of zones and routes
4. Future: Execute autonomous multi-zone mission

## Best Practices

### GPS Quality
- **Good**: HDOP < 2.0 (green indicator)
- **Medium**: HDOP 2.0-5.0 (yellow indicator)  
- **Poor**: HDOP > 5.0 (red indicator)
- **Rule**: Only record routes with HDOP < 2.0

### Recording Technique
1. **Walk slowly**: 0.5 m/s maximum
2. **Steady pace**: Maintain consistent speed
3. **Clear weather**: Avoid rain, heavy cloud cover
4. **Open sky**: Best GPS reception
5. **Add buffer**: Account for 1-2m GPS drift in path width

### Route Types Guide
- **DRIVEWAY**: Wide (3m+), paved, high confidence
- **GATE_PASSAGE**: Narrow (1-2m), requires precision
- **AROUND_BUILDING**: Variable width, corner navigation
- **NARROW_PATH**: Tight spaces, slow speed required
- **ROAD_CROSSING**: Extra caution, potential obstacles

### Safety Considerations
1. Set conservative speed limits (default 0.5 m/s)
2. Mark `mow_during_transit: false` for transit routes
3. Add safety margins to path width
4. Validate routes before autonomous use
5. Re-record routes after property changes

## Troubleshooting

### Poor GPS Quality
- **Symptom**: HDOP > 2.0, waypoints rejected
- **Solution**: Wait for better satellite lock, move to open area
- **Prevention**: Record during clear weather, mid-day (best satellite coverage)

### Routes Not Appearing in Graph
- **Symptom**: Routes recorded but graph not updating
- **Check**: Route has valid from_zone_id and to_zone_id
- **Check**: Both zones exist in zones/ directory
- **Solution**: Refresh web page, verify YAML syntax

### Waypoints Too Sparse
- **Symptom**: Not enough waypoints for smooth path
- **Adjust**: Decrease `waypoint_spacing_meters` parameter
- **Default**: 1.0 meter spacing

### Waypoints Too Dense
- **Symptom**: Excessive waypoints, large file size
- **Adjust**: Increase `waypoint_spacing_meters` parameter
- **Trade-off**: Larger spacing = less detail but smaller files

## Future Enhancements

### Planned Features
- [ ] AprilTag-based gate detection and automated opening
- [ ] Visual odometry for GPS-denied areas
- [ ] Stereo camera obstacle detection on narrow paths
- [ ] Battery-aware route planning (prefer shorter routes when low)
- [ ] Multi-objective optimization (time, battery, wear)
- [ ] Route validation via comparison with new GPS traces
- [ ] Automatic route re-planning on detected obstacles
- [ ] Weather-based route selection (avoid muddy paths in rain)
- [ ] Traffic pattern learning (avoid busy driveways during certain times)

### Research Areas
- Machine learning for optimal path refinement
- Crowd-sourced route sharing between mowers
- Seasonal route adjustments (grass growth patterns)
- Integration with smart home for gate control

## Technical Details

### Dijkstra's Algorithm Implementation
The route planner uses a priority queue-based implementation:
- **Time Complexity**: O((V + E) log V) where V = zones, E = routes
- **Space Complexity**: O(V)
- **Optimality**: Guaranteed shortest path
- **Extension Point**: Can be upgraded to A* with heuristics

### GPS Quality Metrics
- **HDOP** (Horizontal Dilution of Precision): Primary quality metric
- **Threshold**: 2.0 (configurable via parameters)
- **Source**: Derived from NavSatFix.position_covariance
- **Interpretation**: Lower = better (1.0 = ideal, >5.0 = poor)

### Haversine Distance Calculation
Used for GPS waypoint distance:
```python
R = 6371000  # Earth radius in meters
Δφ = lat2 - lat1
Δλ = lon2 - lon1
a = sin²(Δφ/2) + cos(φ1) * cos(φ2) * sin²(Δλ/2)
c = 2 * atan2(√a, √(1-a))
d = R * c
```

## Development

### Building
```bash
# Build messages
colcon build --packages-select rosmower_msgs

# Build nodes
colcon build --packages-select rosmower

# Or build all
colcon build
```

### Testing
```bash
# Run test suite
./test_multi_zone_routes.sh

# Manual testing
ros2 run rosmower route_manager.py
ros2 run rosmower route_planner.py
ros2 topic echo /route/recording/status
```

### Debugging
```bash
# Check topics
ros2 topic list | grep route
ros2 topic echo /routes/all

# Check services
ros2 service list | grep route
ros2 service call /route/record/start std_srvs/srv/Trigger

# Check logs
ros2 node info route_manager
```

## References

- [ROS2 Humble Documentation](https://docs.ros.org/en/humble/)
- [GPS HDOP Explained](https://en.wikipedia.org/wiki/Dilution_of_precision_(navigation))
- [Dijkstra's Algorithm](https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm)
- [Haversine Formula](https://en.wikipedia.org/wiki/Haversine_formula)

## Support

For issues or questions:
1. Check logs: `ros2 node info route_manager`
2. Validate YAML: `python3 -c "import yaml; yaml.safe_load(open('routes/your_route.yaml'))"`
3. Review test results: `./test_multi_zone_routes.sh`
4. Check GPS quality on robot

---

**Version**: 1.0  
**Last Updated**: 2024  
**Maintainer**: ROS Mower Development Team
