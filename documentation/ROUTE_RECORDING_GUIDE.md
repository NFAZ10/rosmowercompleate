# Route Recording Guide

A step-by-step guide to recording safe transit routes between mowing zones.

## What is Route Recording?

Route recording allows you to "teach" the mower safe paths between different mowing zones by walking the desired route while collecting GPS waypoints. The mower will later follow these recorded routes autonomously when transitioning between zones.

## When to Record Routes

Record routes for:
- **Driveways** connecting front and back yards
- **Side passages** around buildings or fences
- **Gate passages** through fenced areas
- **Narrow paths** between obstacles
- **Any transition** between disconnected zones

## Prerequisites

Before recording routes:
1. ✅ All zones must be defined (use Zone Recorder first)
2. ✅ GPS must be receiving signal (HDOP < 2.0)
3. ✅ Clear weather conditions for best GPS accuracy
4. ✅ Web server and route management system running

## Step-by-Step Recording Process

### 1. Access the Route Manager

```bash
# Open in browser
http://<robot-ip>:8080/routes
```

### 2. Check GPS Status

Before recording, verify GPS quality:
- **Green indicator** = Good (HDOP < 2.0) ✅ **Proceed**
- **Yellow indicator** = Medium (HDOP 2-5) ⚠️ **Wait for better signal**
- **Red indicator** = Poor (HDOP > 5) ❌ **Do not record**

**GPS Tips:**
- Wait 2-5 minutes after powering on for GPS lock
- Best signal: Clear sky, mid-day, open area
- Avoid: Heavy clouds, buildings, trees, morning/evening

### 3. Configure Route Parameters

Fill in the route form:

#### **From Zone / To Zone**
Select the starting and ending zones from dropdowns.

**Example:**
- From: `backyard`
- To: `frontyard`

#### **Route Name**
Descriptive name for the route.

**Examples:**
- "Main Driveway"
- "Side Gate Passage"
- "Around Garage"

#### **Route Type**
Choose the appropriate type:

| Type | Description | Use Case |
|------|-------------|----------|
| DRIVEWAY | Wide, paved paths | Main driveways, 3m+ wide |
| GATE_PASSAGE | Narrow passages | Gates, doorways, 1-2m wide |
| AROUND_BUILDING | Routes around structures | Going around house, garage |
| NARROW_PATH | Tight spaces | Between fence and wall |
| ROAD_CROSSING | Crosses roads | Use with caution, low speed |

#### **Max Speed (m/s)**
Maximum autonomous speed for this route.

**Recommendations:**
- Wide driveways: 0.5-0.8 m/s
- Narrow paths: 0.3-0.5 m/s
- Gate passages: 0.2-0.3 m/s
- Road crossings: 0.2-0.4 m/s

**Safety First:** When in doubt, use slower speeds!

#### **Path Width (meters)**
Width of the navigable path.

**How to measure:**
1. Measure physical width of path
2. Add 1-2 meters buffer for GPS drift
3. Example: 2m driveway → set 3-4m path width

#### **Tags**
Comma-separated descriptive tags.

**Examples:**
- "paved, main, wide"
- "narrow, gate, gravel"
- "steep, caution"

#### **Bidirectional**
Can the route be traveled in both directions?

- ✅ **Checked** (default): Route works both ways
- ❌ **Unchecked**: One-way only (rare cases)

**Most routes should be bidirectional.**

#### **Mow During Transit**
Should the mower cut grass while traveling this route?

- ❌ **Unchecked** (default): No mowing, just transit
- ✅ **Checked**: Mow while traveling (if path is grass)

**Typical setting: Unchecked for driveways, sidewalks.**

### 4. Start Recording

1. Click **"Start Recording"** button
2. Recording indicator appears (red, pulsing)
3. Walk to the starting point of your route
4. Begin walking slowly along desired path

**Walking Guidelines:**
- **Speed**: Walk slowly (0.5 m/s or ~1 mph)
- **Pace**: Steady, consistent speed
- **Path**: Stay centered on desired route
- **Stops**: Avoid stopping (use Pause instead)

### 5. During Recording

Monitor the live stats:
- **Waypoints Collected**: Should increase steadily
- **Distance**: Total route distance
- **Duration**: Time elapsed
- **GPS Quality**: Should stay green

**If GPS quality degrades:**
1. Click **"Pause"**
2. Wait for quality to improve
3. Click **"Resume"**
4. Continue walking

**Recording controls:**
- **Pause**: Temporarily stop collecting waypoints
- **Resume**: Continue after pause
- **Stop & Save**: Finish and save route
- **Cancel**: Abort without saving

### 6. Complete Recording

When you reach the destination:
1. Click **"Stop & Save"**
2. Route is validated and saved
3. Confirmation message appears
4. Route appears in route list
5. Zone graph updates automatically

**Minimum requirements:**
- At least 2 waypoints
- Valid from/to zones
- Reasonable distance (> 1 meter)

### 7. Verify Route

After saving:
1. Check route appears in **Recorded Routes** list
2. Verify route shows in **Zone Connectivity Graph**
3. Confirm route details are correct
4. Test route by walking it again (optional)

## Recording Best Practices

### ✅ DO:
- Record during clear weather
- Wait for good GPS (green indicator)
- Walk slowly and steadily
- Stay centered on path
- Add generous path width buffer
- Use conservative speed limits
- Record during mid-day (best GPS)

### ❌ DON'T:
- Record in rain or heavy clouds
- Rush through recording
- Stop and start frequently
- Record with poor GPS (yellow/red)
- Underestimate path width
- Record late evening (poor GPS)
- Skip route validation

## Common Scenarios

### Scenario 1: Simple Driveway Connection

**Setup:**
- Front yard and back yard separated by house
- 3-meter wide paved driveway
- Clear, straight path

**Settings:**
- Route Type: DRIVEWAY
- Max Speed: 0.6 m/s
- Path Width: 4.0 m (3m + 1m buffer)
- Bidirectional: ✅
- Mow During Transit: ❌

**Recording:**
1. Start at front yard edge
2. Walk down driveway at 0.5 m/s
3. Stop at back yard edge
4. Total: 30-40 waypoints, 20-30m distance

### Scenario 2: Narrow Gate Passage

**Setup:**
- Side yard behind 1.5m gate
- Gravel path
- Gate posts on both sides

**Settings:**
- Route Type: GATE_PASSAGE
- Max Speed: 0.3 m/s
- Path Width: 2.5 m (1.5m + 1m buffer)
- Bidirectional: ✅
- Mow During Transit: ❌
- Tags: "narrow, gate, gravel"

**Recording:**
1. Approach gate slowly
2. Walk through center of gate
3. Continue 2-3 meters past gate
4. Total: 10-15 waypoints, 5-8m distance

### Scenario 3: Around Building

**Setup:**
- Path around garage to side yard
- Variable width (2-4m)
- Two 90-degree corners

**Settings:**
- Route Type: AROUND_BUILDING
- Max Speed: 0.4 m/s
- Path Width: 4.0 m
- Bidirectional: ✅
- Mow During Transit: ❌

**Recording:**
1. Start at main yard
2. Walk around building, taking wide corners
3. End at side yard
4. Total: 40-60 waypoints, 30-50m distance

## Troubleshooting

### Problem: No waypoints being collected

**Causes:**
- GPS quality too poor
- Not started recording
- GPS signal lost

**Solutions:**
1. Check GPS quality indicator
2. Verify "Recording" status shows
3. Move to more open area
4. Wait for better GPS lock

### Problem: Too few waypoints

**Causes:**
- Waypoint spacing too large
- GPS skipping points
- Walking too fast

**Solutions:**
1. Walk slower (< 0.5 m/s)
2. Ensure good GPS throughout
3. Check `waypoint_spacing_meters` parameter (default: 1.0m)

### Problem: Route won't save

**Causes:**
- Less than 2 waypoints
- Invalid zone IDs
- GPS never achieved good quality

**Solutions:**
1. Ensure at least 2 waypoints collected
2. Verify zone selections
3. Re-record with better GPS

### Problem: Erratic waypoints

**Causes:**
- Poor GPS quality during recording
- Multipath interference (near buildings)
- GPS drift

**Solutions:**
1. Only record with HDOP < 2.0
2. Avoid recording near large metal structures
3. Add larger path width buffer
4. Re-record in better conditions

## Advanced Techniques

### Multi-Segment Routes

For complex routes with changing conditions:
1. Record separate route segments
2. Create intermediate "waypoint zones"
3. Chain routes: A→B→C instead of direct A→C

**When to use:**
- Routes with drastically different widths
- Combination of paved and grass sections
- Routes requiring different speeds

### Route Validation

After recording, validate by:
1. Walking route again with visualization
2. Checking waypoint density (should be 1-2m apart)
3. Verifying no waypoints in obstacles
4. Testing autonomous following (when implemented)

### Seasonal Updates

Re-record routes when:
- Property layout changes
- Obstacles added/removed
- Gates moved or added
- Seasonal vegetation changes path width

## Safety Checklist

Before using routes autonomously:

- [ ] Route recorded with GPS HDOP < 2.0
- [ ] Path width accounts for GPS drift (1-2m buffer)
- [ ] Speed limit is conservative for route type
- [ ] All waypoints are in safe, navigable areas
- [ ] No waypoints on slopes > 20 degrees
- [ ] No waypoints in water, ditches, or obstacles
- [ ] Route has been visually validated
- [ ] Emergency stop accessible during test runs

## Integration with Zone Recording

Complete workflow:

```
1. Define Zones (Zone Recorder)
   └─► Record front_yard perimeter
   └─► Record back_yard perimeter
   
2. Record Routes (Route Manager)
   └─► Record front_yard → back_yard (driveway)
   └─► Record back_yard → side_yard (gate)
   
3. View Zone Graph
   └─► Verify all zones connected
   └─► Plan multi-zone missions
   
4. Execute Autonomous Mission
   └─► Mower navigates using recorded routes
```

## Quick Reference

| Action | GPS Quality | Speed | Path Width |
|--------|-------------|-------|------------|
| Start Recording | Green (HDOP<2) | - | - |
| Walk Route | Maintain Green | 0.5 m/s | Center of path |
| Wide Driveway | Green | 0.6 m/s | Physical + 1-2m |
| Narrow Gate | Green | 0.3 m/s | Physical + 1-2m |
| Around Building | Green | 0.4 m/s | Physical + 1-2m |

## Next Steps

After recording routes:
1. View routes in Route Manager
2. Check Zone Connectivity Graph
3. Use Route Planner for path finding
4. Test autonomous navigation (when implemented)
5. Record additional routes as needed

---

**Remember:** Quality routes enable safe autonomous operation. Take time to record routes carefully in optimal GPS conditions with appropriate safety margins.
