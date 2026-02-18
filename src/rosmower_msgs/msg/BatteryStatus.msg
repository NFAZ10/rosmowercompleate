# Enhanced battery status message with detailed monitoring
std_msgs/Header header

# Basic measurements
float32 voltage              # Battery voltage (V)
float32 current              # Battery current (A, negative = charging)
float32 percentage           # State of charge (0-100%)

# Computed values
float32 time_to_empty        # Estimated time to empty in minutes (-1 if charging)
float32 time_to_full         # Estimated time to full charge in minutes (-1 if not charging)
float32 capacity_remaining   # Remaining capacity (Ah)
float32 capacity_full        # Full capacity (Ah)

# State information
string state                 # NORMAL, LOW, CRITICAL, CHARGING, CHARGED
bool is_charging             # True if battery is charging
bool low_battery             # True if battery is low
bool critical_battery        # True if battery is critically low

# Temperature (optional, if available)
float32 temperature          # Battery temperature (°C), -999 if not available
