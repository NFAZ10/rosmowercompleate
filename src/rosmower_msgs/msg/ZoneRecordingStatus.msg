# Zone Recording Status Message
# Provides real-time status information during zone boundary recording

# Recording state constants
uint8 STATE_IDLE = 0
uint8 STATE_RECORDING = 1
uint8 STATE_PAUSED = 2

# Current recording state
uint8 state

# Zone being recorded
string zone_name

# Number of waypoints recorded
uint32 waypoint_count

# Total distance traveled (meters)
float64 distance_traveled

# Estimated polygon area (square meters)
float64 estimated_area

# Current GPS fix quality
# 0 = No fix
# 1 = 2D fix
# 2 = 3D fix
# 3 = RTK float
# 4 = RTK fixed
uint8 gps_quality

# GPS horizontal accuracy (meters)
float64 gps_accuracy

# Recording start time
builtin_interfaces/Time start_time

# Last waypoint recording time
builtin_interfaces/Time last_waypoint_time

# Visual odometry available (for future Isaac ROS integration)
bool visual_odometry_available

# Warning/info messages
string status_message
