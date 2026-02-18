# Routes Directory

This directory stores transit routes between mowing zones.

## File Format

Routes are stored as YAML files with the following structure:

```yaml
route_id: "route_001_backyard_to_frontyard"
route_name: "Driveway Route"
from_zone_id: "backyard"
to_zone_id: "frontyard"
route_type: "DRIVEWAY"  # DRIVEWAY, GATE_PASSAGE, AROUND_BUILDING, NARROW_PATH, ROAD_CROSSING
bidirectional: true
max_speed_mps: 0.5
path_width_meters: 2.0
mow_during_transit: false
tags: ["paved", "main"]
created_at: "2024-01-15T10:30:00Z"
waypoints:
  - latitude: 37.12345
    longitude: -122.12345
    altitude: 10.5
  - latitude: 37.12346
    longitude: -122.12346
    altitude: 10.6
total_distance_meters: 15.3
estimated_transit_time_seconds: 30.6
```

## Route Types

- **DRIVEWAY**: Wide paved routes, typically between front and back yards
- **GATE_PASSAGE**: Narrow passages through gates or fences
- **AROUND_BUILDING**: Routes that go around structures
- **NARROW_PATH**: Constrained paths with limited maneuvering room
- **ROAD_CROSSING**: Routes that cross roads or driveways (use caution)

## Best Practices

1. **GPS Quality**: Only record routes with HDOP < 2.0
2. **Speed**: Walk slowly and steadily along the desired path
3. **Weather**: Record in clear weather for best GPS accuracy
4. **Buffer**: Account for 1-2 meter GPS drift in path width
5. **Bidirectional**: Most routes should be bidirectional unless one-way required
6. **Mowing**: Typically set `mow_during_transit: false` for transit routes

## File Naming

Files are automatically named: `{from_zone}_to_{to_zone}_{timestamp}.yaml`

Example: `backyard_to_frontyard_1705330200.yaml`
