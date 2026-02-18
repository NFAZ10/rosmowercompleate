# Phase B Roadmap - Autonomous Mission Execution

**Status:** PENDING (Current: 85% Autonomous)  
**Goal:** Achieve 100% autonomous operation  
**Estimated Time:** 8-10 weeks  
**Started:** Not yet  

---

## 🎯 Phase B Objectives

Transform the robot from **zone/route management capable** to **fully autonomous mowing**.

### What's Missing:
- ❌ Coverage path planning WITHIN zones (how to mow efficiently)
- ❌ Mission execution state machine (autonomous operation)
- ❌ Real-time obstacle avoidance during mowing
- ❌ Coverage tracking (which areas mowed)
- ❌ Mission resumption after charging
- ❌ Adaptive behavior based on conditions

---

## 📋 Phase B Components

### 1️⃣ Coverage Path Planner Node (Week 1)

**File:** `src/rosmower/scripts/coverage_planner.py`

**Purpose:** Generate efficient mowing paths WITHIN zones

**Features:**
- Boustrophedon algorithm (parallel lines with optimal turning)
- Random walk algorithm (alternative for irregular zones)
- Obstacle-aware path adjustment
- Coverage optimization (minimize overlap)
- Integration with Nav2 for path following
- Spiral pattern for circular/irregular zones

**Topics:**
- Subscribe: `/zones` (ZoneArray)
- Publish: `/coverage/path` (nav_msgs/Path)
- Publish: `/coverage/planned` (visualization)

**Services:**
- `/coverage/generate` - Generate path for a zone
- `/coverage/optimize` - Optimize existing path
- `/coverage/validate` - Check path feasibility

**Parameters:**
- `mower_width` - Width of mower deck (meters)
- `overlap_percentage` - Path overlap (default: 10%)
- `algorithm` - 'boustrophedon', 'random', 'spiral'
- `turn_radius` - Minimum turning radius

---

### 2️⃣ Mission Controller Node (Week 1-2)

**File:** `src/rosmower/scripts/mission_controller.py`

**Purpose:** Orchestrate autonomous mowing missions

**State Machine:**
```
IDLE → PLANNING → EXECUTING → PAUSED → CHARGING → RESUMING → COMPLETED
         ↓           ↓           ↓         ↓          ↓
       ERROR ←─────┴───────────┴─────────┴──────────┘
```

**Features:**
- Multi-zone mission sequencing
- Battery-aware pausing/resuming
- Error recovery (GPS loss, obstacle stuck, etc.)
- Mission scheduling (time-based, priority-based)
- Progress tracking and logging
- Integration with zone priorities

**Topics:**
- Subscribe: `/battery/state`, `/zones`, `/routes/all`
- Subscribe: `/mission/command` (String - from battery_monitor)
- Publish: `/mission/status` (Mission)
- Publish: `/mission/current_zone` (Zone)

**Services:**
- `/mission/start` - Start autonomous mission
- `/mission/pause` - Pause current mission
- `/mission/resume` - Resume paused mission
- `/mission/stop` - Stop and save state
- `/mission/abort` - Emergency abort

**Parameters:**
- `zone_sequence` - Order of zones to mow
- `battery_return_threshold` - When to return to dock (%)
- `battery_resume_threshold` - When to resume after charge (%)
- `max_mission_duration` - Maximum time per mission (seconds)

---

### 3️⃣ Coverage Tracker Node (Week 2)

**File:** `src/rosmower/scripts/coverage_tracker.py`

**Purpose:** Track which areas have been mowed

**Features:**
- Grid-based coverage tracking (0.5m x 0.5m cells)
- Coverage heat map generation
- Efficiency metrics calculation
- Missed spot identification
- Persistent coverage storage (resume after reboot)
- Time-based coverage decay (grass grows back)

**Topics:**
- Subscribe: `/odom` (nav_msgs/Odometry)
- Subscribe: `/gps/fix` (sensor_msgs/NavSatFix)
- Publish: `/coverage/map` (OccupancyGrid)
- Publish: `/coverage/stats` (CoverageStats message)

**Services:**
- `/coverage/get_map` - Get coverage map for zone
- `/coverage/reset` - Reset coverage for zone
- `/coverage/get_stats` - Get efficiency metrics

**Parameters:**
- `grid_resolution` - Size of coverage cells (meters)
- `coverage_timeout` - Time before coverage expires (days)
- `overlap_threshold` - When to consider area covered

---

### 4️⃣ Obstacle Integration (Week 2-3)

**Enhancements to existing nodes**

**Real-time LiDAR Integration:**
- Dynamic costmap updates during mowing
- Temporary obstacle avoidance (pets, toys)
- Permanent obstacle mapping
- Safety stop zones (emergency halts)

**Path Re-planning:**
- Local planner adjustments around obstacles
- Global path re-calculation if blocked
- Temporary route deviation
- Obstacle memory (don't retry immediately)

**Integration Points:**
- `coverage_planner.py` - Obstacle-aware initial paths
- `mission_controller.py` - React to obstacle events
- Nav2 costmap configuration

---

### 5️⃣ Web UI Enhancements (Week 3)

**Files:**
- `src/rosmower/web/mission_control.html` (NEW)
- `web_server.py` (add mission endpoints)

**Features:**

**Mission Control Panel:**
- Start/Pause/Stop mission buttons
- Zone selection for missions
- Mission status display
- Emergency stop button
- Mission scheduling interface

**Live Coverage Visualization:**
- Real-time coverage heat map overlay
- Robot position on map (live GPS)
- Planned path preview (green line)
- Completed path (blue line)
- Current zone highlight

**Mission Progress:**
- Overall completion percentage
- Current zone progress
- Time elapsed / estimated remaining
- Battery level during mission
- Distance traveled

**Mission History:**
- Past mission logs
- Efficiency statistics
- Areas needing re-mowing
- Error reports

**API Endpoints:**
```
POST   /api/mission/start
POST   /api/mission/pause
POST   /api/mission/resume
POST   /api/mission/stop
GET    /api/mission/status
GET    /api/mission/history
GET    /api/coverage/map/<zone_id>
GET    /api/coverage/stats
```

---

### 6️⃣ Dock Detection & Alignment (Week 3-4)

**File:** `src/rosmower/scripts/dock_detector.py`

**Purpose:** Autonomous docking for charging

**Features:**

**AprilTag Detection:**
- Camera-based AprilTag detection
- Tag pose estimation (distance, angle)
- Multiple detection strategies (close/far)
- Lighting compensation

**Visual Servo Alignment:**
- PID controller for approach
- Incremental approach phases:
  1. Coarse approach (GPS to ~2m)
  2. Visual acquisition (AprilTag visible)
  3. Fine alignment (±5cm, ±2°)
  4. Final docking (contact sensors)
- Retry logic if alignment fails

**Docking Sequence:**
```
GPS_APPROACH → TAG_SEARCH → VISUAL_SERVO → 
FINAL_ALIGN → DOCK_CONTACT → CHARGING_VERIFY
```

**Topics:**
- Subscribe: `/camera/image_raw` (camera feed)
- Subscribe: `/apriltag/detections` (AprilTag poses)
- Publish: `/dock/status` (DockingStatus)
- Publish: `/cmd_vel` (during alignment)

**Services:**
- `/dock/start` - Start docking sequence
- `/dock/abort` - Abort docking
- `/dock/calibrate` - Calibrate AprilTag pose

**Parameters:**
- `apriltag_id` - ID of dock AprilTag
- `approach_speed` - Speed during approach (m/s)
- `alignment_tolerance` - Position tolerance (meters)
- `angle_tolerance` - Angular tolerance (radians)

---

## 🗓️ Recommended Implementation Schedule

### Week 1-2: Testing & Validation
**Before** implementing Phase B, validate current system:

**Day 1-2:** Field Testing
- Record 2-3 actual yard zones via GPS
- Test GPS quality in various yard areas
- Identify GPS dead zones

**Day 3-4:** Route Recording
- Record routes between zones
- Test bidirectional routes
- Verify route width/speed constraints

**Day 5-7:** Path Planning Tests
- Test multi-zone path planning
- Verify zone graph generation
- Test route optimization

**Day 8-10:** Threshold Tuning
- Tune battery thresholds (25%, 15%)
- Adjust GPS quality thresholds
- Test low battery return behavior

**Day 11-14:** Documentation & Fixes
- Document any issues found
- Fix bugs discovered during testing
- Update configuration parameters

---

### Week 3-4: Coverage Path Planner

**Day 1-3:** Node Creation
- Create `coverage_planner.py` node
- Define message types (CoveragePath.msg)
- Set up ROS2 services

**Day 4-5:** Algorithm Implementation
- Implement boustrophedon algorithm
- Add turn optimization
- Handle obstacle awareness

**Day 6-7:** Testing
- Generate paths for test zones
- Visualize paths in RViz
- Validate path efficiency

**Day 8-10:** Nav2 Integration
- Convert paths to Nav2 waypoints
- Test path following
- Tune path tracking parameters

**Day 11-14:** Field Testing
- Test in actual yard zone
- Measure coverage efficiency
- Identify and fix path issues

---

### Week 5-6: Mission Controller

**Day 1-3:** State Machine
- Create `mission_controller.py`
- Implement state machine
- Define state transitions

**Day 4-5:** Battery Integration
- Battery-aware mission pausing
- Return-to-dock logic
- Mission resumption after charge

**Day 6-7:** Multi-Zone Sequencing
- Zone priority handling
- Route following between zones
- Zone transition logic

**Day 8-10:** Error Recovery
- GPS loss handling
- Obstacle stuck detection
- Communication loss recovery

**Day 11-14:** Full Test
- Multi-zone autonomous mission
- Battery pause/resume test
- Error scenario testing

---

### Week 7-8: Coverage Tracking & UI

**Day 1-3:** Coverage Tracker
- Create `coverage_tracker.py`
- Grid-based tracking algorithm
- Persistent storage

**Day 4-5:** Heat Map Generation
- Coverage map publishing
- Efficiency metrics
- Missed spot detection

**Day 6-7:** Web UI Development
- Create `mission_control.html`
- Live coverage visualization
- Real-time robot position

**Day 8-10:** Mission Control Panel
- Start/pause/stop controls
- Mission scheduling interface
- Status displays

**Day 11-14:** Integration & Polish
- Integrate all UI components
- Add mission history
- Improve visualizations

---

### Week 9-10: Docking & Final Integration

**Day 1-3:** AprilTag Setup
- Install AprilTag on dock
- Camera calibration
- Tag detection testing

**Day 4-5:** Docking Algorithm
- Visual servo implementation
- Alignment PID tuning
- Retry logic

**Day 6-7:** Docking Tests
- Autonomous docking tests
- Various lighting conditions
- Approach angle variations

**Day 8-10:** Full System Integration
- End-to-end autonomous operation
- Multi-zone mission with docking
- Battery cycle testing

**Day 11-14:** Field Optimization
- Real-world testing
- Performance optimization
- Bug fixes and refinement

---

## 🎯 Quick Win Alternative: Simple Random Walk

Before full boustrophedon implementation, consider this simpler approach:

**Time:** 1-2 days  
**Complexity:** Low  
**Benefit:** Proves autonomous concept quickly  

### Random Walk Algorithm:
```python
def generate_random_path(zone, duration=300):
    """Generate random waypoints within zone for N seconds"""
    waypoints = []
    current_pos = zone.centroid
    
    for _ in range(duration // 10):  # New waypoint every 10s
        # Random heading
        heading = random.uniform(0, 2*pi)
        distance = random.uniform(2, 5)  # 2-5 meters
        
        # Calculate new position
        new_pos = current_pos + (distance * heading_vector)
        
        # Keep inside zone
        if zone.contains(new_pos):
            waypoints.append(new_pos)
            current_pos = new_pos
    
    return waypoints
```

**Pros:** Simple, works immediately, good for testing  
**Cons:** Inefficient coverage, lots of overlap  
**Use Case:** Initial autonomous testing, proof of concept  

---

## 🔧 Integration with Existing System

### Current System (Phase A + Multi-Zone Routes):
```
battery_monitor.py → Monitors battery, triggers dock commands
zone_manager.py → Manages zones, publishes zone list
zone_recorder.py → Records zone boundaries via GPS
route_manager.py → Records routes between zones
route_planner.py → Plans multi-hop routes (A→B→C)
```

### Phase B Additions:
```
coverage_planner.py → Generates mowing paths IN zones
mission_controller.py → Orchestrates autonomous operation
coverage_tracker.py → Tracks mowed areas
dock_detector.py → Autonomous docking
```

### Data Flow:
```
User → Starts Mission via Web UI
     ↓
mission_controller → Reads zones, battery, routes
     ↓
coverage_planner → Generates path for Zone 1
     ↓
Nav2 → Follows path, avoids obstacles
     ↓
coverage_tracker → Marks areas as mowed
     ↓
[Battery Low] → mission_controller pauses mission
     ↓
route_planner → Plans route to dock
     ↓
Nav2 → Follows route to dock
     ↓
dock_detector → Aligns and docks
     ↓
[Charging Complete] → mission_controller resumes
     ↓
Repeat until all zones complete
```

---

## 📊 Success Metrics

### Coverage Efficiency:
- Target: >85% coverage in single pass
- Overlap: <15% redundant mowing
- Time: Complete yard in <2 hours

### Battery Performance:
- Return-to-dock reliability: >95%
- Successful docking rate: >90%
- Mission resumption: 100%

### Reliability:
- Obstacle detection: 100% (safety critical)
- GPS-based navigation: >90% accuracy
- Mission completion: >95%

### User Experience:
- Mission setup time: <5 minutes
- Manual intervention: <10% of missions
- Error recovery: Automatic in >80% of cases

---

## 🚨 Critical Dependencies

### Before Starting Phase B:

1. **LiDAR must be working reliably** ⚠️ (Current Issue!)
   - Required for obstacle detection
   - Safety-critical component
   - Must be fixed before autonomous operation

2. **GPS must have acceptable accuracy**
   - RTK preferred: ±2-5cm
   - 3D Fix minimum: ±2m
   - Test in actual yard first

3. **Nav2 stack must be configured**
   - Costmap parameters tuned
   - Path planning working
   - Recovery behaviors defined

4. **Battery monitoring must be accurate**
   - Thresholds validated
   - State transitions working
   - Dock commands triggering correctly

5. **Zones and routes must be recorded**
   - At least 1-2 test zones
   - Routes between zones (if multi-zone)
   - Zone graph validated

---

## 📝 Notes & Considerations

### GPS Drift Mitigation:
- Use sensor fusion (GPS + wheel odometry + IMU)
- Consider visual odometry for narrow paths
- Implement path corridor tolerance (±0.5m)

### Weather Considerations:
- Rain detection → pause mission
- Temperature monitoring → battery performance
- Wet grass → reduce speed

### Obstacle Handling Philosophy:
- **Temporary obstacles** (pets, toys): Avoid, retry later
- **Permanent obstacles** (trees, rocks): Map and avoid permanently
- **Unknown obstacles**: Conservative avoidance, log for review

### Coverage Strategy:
- Start with simple parallel lines
- Add spiral patterns for irregular zones
- Consider time-of-day (avoid hot midday)
- Grass height feedback (if sensor available)

---

## 🎓 Learning Resources

### ROS2 Path Planning:
- Nav2 documentation: https://navigation.ros.org/
- Coverage path planning: https://github.com/nobleo/coverage_path_planning
- Boustrophedon decomposition papers

### AprilTag Docking:
- AprilTag ROS2: https://github.com/christianrauch/apriltag_ros
- Visual servoing techniques
- PID control tuning

### State Machines:
- SMACH for ROS2
- BehaviorTree.CPP
- Simple Python state machines

---

## 🔄 Returning to This Document

This roadmap is saved at: `/mnt/nova_ssd/rosmowercompleate/PHASE_B_ROADMAP.md`

**To resume Phase B work:**
```bash
# Read the roadmap
cat PHASE_B_ROADMAP.md

# Check where you left off
grep -n "❌\|TODO\|PENDING" PHASE_B_ROADMAP.md

# Start with the recommended sequence
# Week 1-2: Test current system first!
```

---

**Status:** Saved for future implementation  
**Priority:** HIGH (after LiDAR fix)  
**Next Action:** Fix LiDAR intermittent failure issue  
**Last Updated:** February 11, 2026  

---

*Remember: A working foundation is more important than new features. Fix the LiDAR before proceeding with autonomous operation!*
