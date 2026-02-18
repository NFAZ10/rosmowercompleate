# Mission message for autonomous mowing
std_msgs/Header header

# Mission identification
string mission_id            # Unique mission identifier
string mission_type          # MOW_ZONE, RETURN_TO_DOCK, PATROL, EMERGENCY_DOCK

# Zone information (for MOW_ZONE missions)
string zone_id               # Zone to mow (empty if not zone-based)
string[] zone_ids            # Multiple zones to mow in sequence

# Mission parameters
uint8 priority               # Mission priority (0-255, higher = more important)
bool preemptable             # Can this mission be interrupted?
float32 coverage_target      # Target coverage percentage (0-100)

# Status
string status                # PENDING, ACTIVE, PAUSED, COMPLETED, FAILED, CANCELLED
float32 progress             # Progress percentage (0-100)
string error_message         # Error message if status is FAILED

# Timing
builtin_interfaces/Time created_at
builtin_interfaces/Time started_at
builtin_interfaces/Time completed_at
