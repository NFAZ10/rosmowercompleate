# Route Recording Best Practices

Expert tips for recording high-quality, reliable transit routes.

## GPS Quality is Paramount

### Understanding HDOP (Horizontal Dilution of Precision)

HDOP measures GPS accuracy:
- **< 1.0**: Ideal (rarely achieved outdoors)
- **1.0-2.0**: Excellent ✅ **Record routes**
- **2.0-5.0**: Good ⚠️ **Acceptable but not ideal**
- **5.0-10.0**: Fair ❌ **Do not record**
- **> 10.0**: Poor ❌ **No GPS lock**

**Rule of Thumb:** Only record routes with HDOP < 2.0

### Optimizing GPS Reception

**Best conditions:**
- ☀️ Clear sky, minimal cloud cover
- 🕐 Mid-day (10 AM - 2 PM) when most satellites overhead
- 🌲 Open areas away from trees and buildings
- 🏞️ Level terrain with good horizon visibility

**Avoid:**
- 🌧️ Rain, heavy clouds, storms
- 🌆 Urban canyons (tall buildings)
- 🌲 Under dense tree canopy
- 🌄 Early morning/late evening (fewer satellites)
- 📡 Near radio/cell towers (interference)

### GPS Warm-up

Always allow GPS to stabilize:
1. Power on mower
2. Wait 2-5 minutes for satellite lock
3. Watch HDOP value decrease
4. Start recording when HDOP < 2.0

## Walking Technique

### Speed Control

**Optimal recording speed: 0.5 m/s (1.1 mph)**

Why slow is better:
- More waypoints per meter
- Better GPS averaging
- Clearer path representation
- Easier to maintain center line

**Too fast (> 1.0 m/s):**
- Sparse waypoints
- GPS lag causes inaccuracy
- Hard to stay centered

**Too slow (< 0.3 m/s):**
- GPS jitter more pronounced
- Unnecessary waypoint density
- Takes longer to record

### Path Positioning

**Stay centered on your intended route:**

```
     Correct:           Incorrect:
     
    ▓▓▓▓▓▓▓▓▓          ▓▓▓▓▓▓▓▓▓
    ▓  👤  ▓          ▓👤    ▓
    ▓  ↓   ▓          ▓ ↓    ▓
    ▓  👤  ▓          ▓  👤  ▓
    ▓▓▓▓▓▓▓▓▓          ▓▓▓▓▓▓▓▓▓
   
   Centered          Off-center
   ✅ Good          ❌ Bad
```

**Tips:**
- Use visual landmarks to maintain center
- Walk straight lines where possible
- Take wide, smooth corners
- Avoid zigzagging

### Handling Corners

**For 90-degree corners:**

```
Before corner:          At corner:           After corner:
┌─────────────          ┌─────────────       ┌─────────────
│                       │  ╭───────────       │  │
│  ↓                    │  ↓                  │  │
│  👤                   │  👤╮                │  │
│                       │                     │  ↓
                                              │  👤

Slow down            Round corner          Resume speed
```

1. Slow down before corner
2. Round the corner (don't cut it)
3. Maintain 1-2 meter clearance from obstacles
4. Resume normal speed after corner

## Path Width Guidelines

### GPS Drift Buffer

GPS can drift 1-3 meters from true position even with good HDOP.

**Always add buffer:**

Physical width → Recorded width
- 2.0m path → 3.5-4.0m recorded
- 3.0m path → 4.5-5.0m recorded
- 1.5m gate → 2.5-3.0m recorded

**Formula:**
```
Recorded Width = Physical Width + (2 × GPS Drift Buffer)
GPS Drift Buffer = 1.0-1.5 meters
```

### Width by Route Type

| Route Type | Typical Physical | Recorded Width | Reason |
|------------|------------------|----------------|--------|
| Wide Driveway | 3.0-4.0m | 5.0-6.0m | Generous buffer |
| Standard Path | 2.0-3.0m | 4.0-4.5m | Safe clearance |
| Narrow Path | 1.5-2.0m | 3.0-3.5m | Minimal viable |
| Gate Passage | 1.0-1.5m | 2.5-3.0m | Critical accuracy |

**Red flags:**
- ❌ Recorded width < physical width (too narrow!)
- ❌ Path width = exact physical width (no GPS buffer)
- ✅ Recorded width = physical + 2-3 meters (good)

## Speed Limit Selection

### Conservative Defaults

**Safety-first approach:** Use slower speeds initially, increase after testing.

| Route Type | Initial Speed | After Testing | Maximum |
|------------|---------------|---------------|---------|
| DRIVEWAY (wide) | 0.4 m/s | 0.6 m/s | 0.8 m/s |
| AROUND_BUILDING | 0.3 m/s | 0.5 m/s | 0.6 m/s |
| NARROW_PATH | 0.2 m/s | 0.3 m/s | 0.4 m/s |
| GATE_PASSAGE | 0.2 m/s | 0.3 m/s | 0.3 m/s |
| ROAD_CROSSING | 0.3 m/s | 0.4 m/s | 0.5 m/s |

### Factors Affecting Speed

**Reduce speed for:**
- Narrow passages (< 2m width)
- Sharp corners (< 90°)
- Slopes > 10 degrees
- Gravel or uneven surfaces
- High-traffic areas
- Poor visibility zones

**Can increase speed for:**
- Wide, straight paths (> 3m)
- Paved surfaces
- Level terrain
- Bidirectional routes (can slow down as needed)

## Weather and Timing

### Ideal Recording Conditions

**Perfect day:**
- ☀️ Clear blue sky
- 🌡️ 50-80°F (10-27°C)
- 💨 Light wind (< 10 mph)
- 🕐 10 AM - 2 PM
- 📅 Monday-Friday (less satellite traffic)

### Avoid These Conditions

**Never record in:**
- 🌧️ Rain (GPS accuracy degrades)
- ⛈️ Thunderstorms (dangerous + poor GPS)
- 🌁 Heavy fog (GPS can be affected)
- ❄️ Snow (path obscured, GPS degraded)

**Wait for better conditions:**
- ☁️ Overcast (HDOP may be elevated)
- 🌅 Sunrise/sunset (fewer satellites visible)
- 🌙 Night (no visibility for visual checks)

## Route Types - Deep Dive

### DRIVEWAY Routes

**Characteristics:**
- Wide (3m+)
- Usually paved
- Straight or gentle curves
- High confidence navigation

**Best practices:**
- Record center line
- Note any drainage grates or obstacles
- Mark any slopes > 15 degrees
- Set higher speed (0.5-0.6 m/s)

### GATE_PASSAGE Routes

**Characteristics:**
- Narrow (1-2m)
- Fixed obstacles on sides (posts, walls)
- Critical precision required

**Best practices:**
- Record multiple passes if possible
- Use minimum viable speed (0.2-0.3 m/s)
- Set path width conservatively
- Tag with "critical" or "narrow"
- Future: Add AprilTag markers

### AROUND_BUILDING Routes

**Characteristics:**
- Variable width
- Multiple corners
- Potential GPS multipath (near walls)

**Best practices:**
- Record away from walls (50cm+)
- Round all corners widely
- Note any tight sections
- Consider breaking into segments

### NARROW_PATH Routes

**Characteristics:**
- Constrained width (1.5-2.5m)
- May have vegetation on sides
- Requires careful navigation

**Best practices:**
- Record at slowest speed
- Path width = minimum safe width
- Check clearance for mower width
- Plan seasonal re-recording (vegetation growth)

### ROAD_CROSSING Routes

**Characteristics:**
- Crosses driveways or roads
- Potential for traffic
- Safety critical

**Best practices:**
- Use slow speed (0.3-0.4 m/s)
- Tag with "caution" or "road"
- Consider time-of-day restrictions
- Add visual check waypoints (future)

## Validation and Testing

### Post-Recording Validation

**Immediately after saving:**

1. **Visual Check:**
   - View route in route list
   - Verify waypoint count (should be distance/1m)
   - Check distance matches expected
   - Confirm from/to zones correct

2. **Graph Check:**
   - Route appears in zone graph
   - Edge connects correct nodes
   - Bidirectional if expected

3. **Data Check:**
   ```yaml
   waypoints: 25+  # For 25m route with 1m spacing
   total_distance_meters: 20-30  # Reasonable
   estimated_transit_time_seconds: 40-60  # ~0.5m/s
   ```

### Walk-Through Validation

Before autonomous use:

1. Walk route again with GPS display
2. Compare actual path to waypoints
3. Note any sections with poor accuracy
4. Re-record problem sections if needed

### Autonomous Test

When ready for autonomous testing:

1. Start with manual control nearby
2. Test single route at slow speed
3. Monitor mower staying within corridor
4. Adjust path width if needed
5. Re-record if mower consistently off-path

## Common Mistakes and Fixes

### Mistake 1: Recording in Poor GPS

**Symptom:** Waypoints jump around, erratic path

**Fix:**
- Delete route
- Wait for HDOP < 2.0
- Re-record in better conditions

### Mistake 2: Walking Too Fast

**Symptom:** Very few waypoints, large gaps

**Fix:**
- Reduce walking speed to 0.5 m/s
- Re-record at proper speed

### Mistake 3: Insufficient Path Width

**Symptom:** Mower goes off-path or stops frequently

**Fix:**
- Edit route YAML, increase `path_width_meters`
- Or re-record with wider corridor

### Mistake 4: Not Centered on Path

**Symptom:** Route hugs one side of path

**Fix:**
- Re-record staying centered
- Use visual guides to maintain center

### Mistake 5: Sharp Corners

**Symptom:** Waypoints cut corners, mower can't follow

**Fix:**
- Re-record with rounded corners
- Slow down through corners
- Add extra clearance

## Advanced Techniques

### Multi-Pass Recording

For critical routes, record multiple times:

1. Record route A→B
2. Record route B→A  
3. Compare waypoint patterns
4. Use route with better GPS quality
5. Average waypoints if both good (future enhancement)

### Seasonal Route Variants

For routes affected by vegetation:

- Record "summer" route (narrower due to growth)
- Record "winter" route (wider when vegetation dies)
- Switch routes based on season

### Waypoint Density Optimization

Adjust `waypoint_spacing_meters` parameter:

**Dense spacing (0.5m):**
- Use for: Narrow paths, complex routes
- Pro: Very smooth path following
- Con: Large file size, slower processing

**Standard spacing (1.0m):**
- Use for: Most routes
- Pro: Good balance
- Con: None for typical use

**Sparse spacing (2.0m):**
- Use for: Wide, straight driveways
- Pro: Smaller files, faster processing
- Con: Less detail, may miss features

## Checklist for Perfect Routes

Before recording:
- [ ] GPS HDOP < 2.0 (green indicator)
- [ ] Clear weather, good visibility
- [ ] Mid-day time (10 AM - 2 PM)
- [ ] Both zones defined and saved
- [ ] Route parameters configured
- [ ] Walking speed comfortable (0.5 m/s)

During recording:
- [ ] GPS quality stays green
- [ ] Walking at steady pace
- [ ] Staying centered on path
- [ ] Waypoints incrementing regularly
- [ ] Distance increasing smoothly

After recording:
- [ ] Minimum 2 waypoints collected
- [ ] Distance matches expected length
- [ ] Route appears in route list
- [ ] Zone graph shows connection
- [ ] Route details look correct

Before autonomous use:
- [ ] Route validated with walk-through
- [ ] Path width has GPS buffer (physical + 2m)
- [ ] Speed limit is conservative
- [ ] Emergency stop tested and accessible
- [ ] Route marked as tested

## Resources

### GPS Quality Monitoring

Check GPS quality before recording:
```bash
# Inside Docker container
ros2 topic echo /gps/fix --field position_covariance[0]
# Values < 4.0 indicate HDOP < 2.0
```

### Waypoint Spacing Adjustment

Edit route manager parameters:
```python
'waypoint_spacing_meters': 1.0  # Default
'waypoint_spacing_meters': 0.5  # Dense
'waypoint_spacing_meters': 2.0  # Sparse
```

### Route Analysis

Analyze recorded route:
```bash
# Count waypoints
cat routes/your_route.yaml | grep "latitude:" | wc -l

# Check distance
cat routes/your_route.yaml | grep "total_distance_meters:"
```

## Summary

**Golden Rules:**
1. 🎯 GPS HDOP < 2.0 always
2. 🐌 Walk slowly (0.5 m/s)
3. 📏 Add GPS buffer to path width
4. 🛡️ Be conservative with speed limits
5. ☀️ Record in ideal weather
6. 🎨 Stay centered on path
7. ✅ Validate before autonomous use

**Remember:** 30 minutes of careful route recording saves hours of troubleshooting later!

---

**Next:** See [ROUTE_RECORDING_GUIDE.md](ROUTE_RECORDING_GUIDE.md) for step-by-step instructions.
