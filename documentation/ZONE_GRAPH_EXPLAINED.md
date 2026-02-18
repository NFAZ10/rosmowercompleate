# Zone Graph Explained

Understanding zone connectivity and graph-based path planning for autonomous multi-zone mowing.

## What is a Zone Graph?

A **zone graph** is a mathematical representation of your property's mowing zones and the routes connecting them. It allows the autonomous mower to reason about which zones it can reach and plan optimal paths between them.

## Graph Theory Basics

### Nodes (Vertices)
**Nodes represent mowing zones.**

Each node contains:
- `zone_id`: Unique identifier (e.g., "backyard")
- `zone_name`: Human-readable name (e.g., "Back Yard")
- `center_lat`, `center_lon`: Geographic center of zone
- `priority`: Mowing priority (0 = highest, 255 = lowest)
- `last_mowed`: Timestamp of last mowing
- `estimated_mow_time_seconds`: Expected time to mow

**Example node:**
```yaml
zone_id: backyard
zone_name: "Back Yard"
center_lat: 37.12345
center_lon: -122.12345
priority: 5
estimated_mow_time_seconds: 600
```

### Edges
**Edges represent transit routes between zones.**

Each edge contains:
- `from_zone_id`: Starting zone
- `to_zone_id`: Ending zone
- `route_id`: Reference to full route definition
- `distance_meters`: Route length
- `transit_time_seconds`: Expected traversal time
- `bidirectional`: Can be traveled both ways?

**Example edge:**
```yaml
from_zone_id: backyard
to_zone_id: frontyard
route_id: route_driveway_001
distance_meters: 25.5
transit_time_seconds: 51.0
bidirectional: true
```

### Graph Structure

```
        Zone A (Front Yard)
             │
             │ Route 1 (Driveway)
             │ 25m, bidirectional
             │
        Zone B (Back Yard)
             │
             │ Route 2 (Gate)
             │ 10m, bidirectional
             │
        Zone C (Side Yard)
```

In graph notation:
- **Nodes**: {A, B, C}
- **Edges**: {(A,B), (B,C)}
- **Bidirectional**: (A,B) also means (B,A)

## Graph Generation

### Automatic Generation

The zone manager automatically generates the zone graph:

1. **Collect Zones**: Load all defined zones from `/ws/zones/`
2. **Calculate Centers**: Compute geographic center of each zone's perimeter
3. **Load Routes**: Read all route definitions from `/ws/routes/`
4. **Create Nodes**: One node per zone with metadata
5. **Create Edges**: One edge per route connecting zones
6. **Publish**: Send updated graph to `/zones/graph` topic

### Update Triggers

Graph regenerates when:
- New zone is added
- Zone is deleted
- New route is recorded
- Route is deleted
- Zone priority is updated

## Connectivity Analysis

### Connected Zones

Two zones are **connected** if a route exists between them.

**Direct connection:**
```
A ←→ B   (bidirectional route exists)
```

**Indirect connection:**
```
A ←→ B ←→ C
(A can reach C via B)
```

### Disconnected Zones

Zones with no path between them are **disconnected**.

```
A ←→ B    C ←→ D

A cannot reach C or D
C cannot reach A or B
```

**When this happens:**
- Multi-zone missions cannot include disconnected zones
- Route planner will report "no path found"
- Solution: Record connecting routes

### Graph Components

A **connected component** is a set of zones where all zones can reach all other zones.

**Example:**
```
Component 1: {Front, Back, Side}
Component 2: {Remote}
```

If you have multiple components, you need to record routes to connect them.

## Path Planning Algorithms

### Dijkstra's Algorithm

The route planner uses **Dijkstra's algorithm** to find the shortest path between zones.

**How it works:**

1. **Initialize:**
   - Set distance to start zone = 0
   - Set distance to all other zones = ∞
   - Create empty visited set

2. **Iterate:**
   - Select unvisited zone with smallest distance
   - For each neighbor:
     - Calculate distance via current zone
     - Update if shorter than known distance
   - Mark current zone as visited

3. **Terminate:**
   - When destination reached
   - Or all reachable zones visited

**Example:**

```
Find path from A to D:

    A ─5m─ B ─10m─ D
    │              │
    15m           3m
    │              │
    C ────8m─────┘

Step 1: Start at A (distance = 0)
Step 2: Check neighbors B (5m), C (15m)
Step 3: Visit B (5m), check D (15m)
Step 4: Visit C (15m), check D (23m via C)
Step 5: Visit D (15m via B) ✓

Shortest path: A → B → D (15m)
```

### Time Complexity

- **Vertices (V)**: Number of zones
- **Edges (E)**: Number of routes
- **Complexity**: O((V + E) log V)

**Performance:**
- 5 zones, 10 routes: < 1ms
- 20 zones, 50 routes: < 5ms
- 100 zones, 300 routes: < 50ms

More than sufficient for typical properties!

## Graph Visualization

### Web Interface Graph

The web interface displays an interactive graph visualization:

**Layout:**
- Nodes positioned in circle
- Edges drawn as lines between nodes
- Arrows show direction (if not bidirectional)

**Interpretation:**

```
    ●───────●
    │       │
    │   ●───┘
    │   │
    ●───┘

4 zones, 5 routes (all bidirectional)
Fully connected graph
```

**Color coding:**
- **Nodes (circles)**: Zones (labeled with names)
- **Edges (lines)**: Routes
- **Arrows**: One-way routes
- **No arrow**: Bidirectional routes

### Graph Properties

**Fully Connected:**
All zones can reach all other zones.
```
✓ Good for multi-zone missions
✓ Maximum flexibility
```

**Partially Connected:**
Some zones cannot reach others.
```
⚠️ Limited multi-zone routing
⚠️ Need to record more routes
```

**Disconnected:**
Multiple separate components.
```
❌ Cannot route between components
❌ Must record connecting routes
```

## Use Cases

### Use Case 1: Shortest Path

**Problem:** Find quickest route from front yard to side yard.

**Graph:**
```
Front ─25m─ Back ─10m─ Side
  │                      │
  └──────45m─────────────┘
```

**Solution:**
```python
path, distance = dijkstra("front", "side")
# Returns: ["front", "back", "side"], 35m
# Avoids longer direct route (45m)
```

### Use Case 2: Multi-Zone Mission

**Problem:** Mow all zones starting from charging dock.

**Graph:**
```
    Dock
     │
    Front ─ Back
     │       │
    Side ────┘
```

**Solution:**
```python
zones = ["front", "back", "side"]
current = "dock"
for zone in zones:
    path, dist = dijkstra(current, zone)
    navigate(path)
    mow_zone(zone)
    current = zone
# Return to dock
path, dist = dijkstra(current, "dock")
navigate(path)
```

### Use Case 3: Priority-Based Routing

**Problem:** Mow high-priority zones first (e.g., front yard for visibility).

**Zones:**
- Front Yard: Priority 1 (high visibility)
- Back Yard: Priority 5 (low visibility)
- Side Yard: Priority 3 (medium)

**Solution:**
```python
zones_by_priority = sorted(zones, key=lambda z: z.priority)
# Returns: [front, side, back]

for zone in zones_by_priority:
    path = dijkstra(current_location, zone)
    navigate_and_mow(path, zone)
```

### Use Case 4: Battery-Aware Routing

**Problem:** Plan route considering battery limitations.

**Future enhancement:**
```python
def plan_battery_aware_route(start, zones, battery_level):
    """Plan route that completes within battery capacity"""
    
    # Estimate time for each zone
    total_time = 0
    route = []
    
    for zone in zones:
        path, dist = dijkstra(current, zone)
        transit_time = estimate_transit_time(path)
        mow_time = zone.estimated_mow_time
        
        if total_time + transit_time + mow_time < battery_capacity:
            route.append(zone)
            total_time += transit_time + mow_time
            current = zone
        else:
            # Return to dock to recharge
            break
    
    # Add return to dock
    path_home = dijkstra(current, "dock")
    
    return route, total_time
```

## Advanced Concepts

### Weighted Edges

Edges can have multiple weights:

**Distance-based:**
```python
weight = route.total_distance_meters
```

**Time-based:**
```python
weight = route.estimated_transit_time_seconds
```

**Cost-based (future):**
```python
weight = (
    distance * distance_cost +
    time * time_cost +
    terrain_difficulty * difficulty_cost
)
```

### Directed vs Undirected Edges

**Undirected (bidirectional):**
```
A ←→ B
Can travel A→B or B→A
```

**Directed (one-way):**
```
A → B
Can only travel A→B
Rare in lawn mowing, but possible for:
- One-way steep slopes
- One-way gates
```

### Graph Algorithms

**Current implementation:**
- ✅ Dijkstra's shortest path

**Future implementations:**
- A* with heuristics (faster for large graphs)
- Floyd-Warshall (all-pairs shortest paths)
- Traveling Salesman (optimal zone visit order)
- Minimum Spanning Tree (minimal route network)

## Graph Maintenance

### Adding New Zones

When you add a new zone:
1. Zone is added to graph as isolated node
2. No edges initially (not connected)
3. Record routes to connect it
4. Graph automatically updates

### Deleting Zones

When you delete a zone:
1. Node is removed from graph
2. All edges to/from that zone are removed
3. May disconnect other zones
4. Check graph connectivity after deletion

### Route Updates

When routes change:
1. Edit route YAML file
2. Graph automatically regenerates on next update
3. Path planning uses new route parameters

### Seasonal Adjustments

**Winter:**
- Some routes may be impassable (snow)
- Temporarily mark routes as unavailable
- Graph automatically recalculates accessible zones

**Spring:**
- Re-enable winter routes
- Re-record routes affected by frost heave
- Update route parameters for new conditions

## Troubleshooting

### Problem: Zones not connected in graph

**Symptoms:**
- Route exists but doesn't show in graph
- Path planner can't find route between zones

**Causes:**
1. Route missing `from_zone_id` or `to_zone_id`
2. Zone IDs don't match zone filenames
3. Route YAML syntax error

**Solutions:**
```bash
# Check route file
cat routes/your_route.yaml | grep "zone_id"

# Verify zone IDs match
ls zones/  # Should show: backyard.yaml, frontyard.yaml
# Route should reference: backyard, frontyard
```

### Problem: Shortest path not optimal

**Symptoms:**
- Planner chooses longer route
- Unexpected path through intermediate zones

**Causes:**
- Edge weights incorrect
- Missing direct route
- Route parameters not updated

**Solutions:**
1. Verify route distances are accurate
2. Check if direct route exists
3. Re-record routes if needed

### Problem: Graph not updating

**Symptoms:**
- New routes don't appear in graph
- Web visualization stale

**Causes:**
- Route manager not running
- Zone manager not receiving route updates
- Web page not refreshing

**Solutions:**
```bash
# Restart route manager
ros2 run rosmower route_manager.py

# Check topics
ros2 topic echo /zones/graph --once

# Refresh web page
```

## Visualization Examples

### Simple Property

```
Front Yard ←─Driveway─→ Back Yard

Nodes: 2
Edges: 1 (bidirectional)
Fully connected: Yes
```

### Medium Property

```
      Front
        │
     Driveway
        │
      Back ←─Gate─→ Side

Nodes: 3
Edges: 2 (both bidirectional)
Fully connected: Yes
```

### Complex Property

```
    Front ←─Drive─→ Back
      │               │
     Path            Gate
      │               │
    Side1 ←─Path─→ Side2

Nodes: 4
Edges: 4 (all bidirectional)
Fully connected: Yes
Multiple paths between most zones
```

### Disconnected Property

```
Main Property:          Remote Area:
Front ←→ Back          Garden ←→ Shed

Component 1: {Front, Back}
Component 2: {Garden, Shed}

Action needed: Record route connecting components
```

## Mathematical Representation

### Adjacency Matrix

For zones A, B, C:

```
     A   B   C
A  [ 0  25   ∞ ]
B  [25   0  10 ]
C  [ ∞  10   0 ]

0 = same zone
∞ = no direct route
Numbers = route distance in meters
```

### Adjacency List

```python
graph = {
    'A': [('B', 25)],
    'B': [('A', 25), ('C', 10)],
    'C': [('B', 10)]
}
```

More efficient for sparse graphs (typical for properties).

## Performance Optimization

### For Large Properties (20+ zones)

**Optimizations:**
1. Cache graph in memory (already implemented)
2. Only regenerate on changes (already implemented)
3. Use A* instead of Dijkstra (future)
4. Precompute all-pairs shortest paths (future)

### Memory Usage

**Typical property (5 zones, 10 routes):**
- Graph: ~2 KB in memory
- YAML storage: ~5 KB on disk

**Large property (50 zones, 150 routes):**
- Graph: ~50 KB in memory
- YAML storage: ~150 KB on disk

Negligible even on embedded systems!

## Summary

The zone graph:
- ✅ Represents property as connected zones
- ✅ Enables intelligent path planning
- ✅ Supports multi-zone autonomous missions
- ✅ Updates automatically when zones/routes change
- ✅ Scales efficiently to large properties

**Key insight:** By modeling your property as a graph, the mower can reason about optimal routes just like you do mentally when planning your mowing schedule!

---

**Next Steps:**
- Record routes to connect all your zones
- Check graph visualization in web UI
- Plan multi-zone missions
- Let the mower optimize its own path!

**See Also:**
- [MULTI_ZONE_GUIDE.md](MULTI_ZONE_GUIDE.md) - System overview
- [ROUTE_RECORDING_GUIDE.md](ROUTE_RECORDING_GUIDE.md) - Recording routes
