std_msgs/Header header
string route_id
string route_name
string from_zone_id
string to_zone_id
string route_type  # DRIVEWAY, GATE_PASSAGE, AROUND_BUILDING, NARROW_PATH, ROAD_CROSSING
bool bidirectional
float32 max_speed_mps  # meters per second
float32 path_width_meters
bool mow_during_transit  # usually false for transit routes
sensor_msgs/NavSatFix[] waypoints
float32 total_distance_meters
float32 estimated_transit_time_seconds
string[] tags  # e.g., ["narrow", "gate", "gravel"]
builtin_interfaces/Time created_at
builtin_interfaces/Time last_validated
