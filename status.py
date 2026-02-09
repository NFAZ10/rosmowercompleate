#!/usr/bin/env python3
import argparse, math, os, sys, time, threading
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, QoSReliabilityPolicy, QoSHistoryPolicy
from rclpy.time import Time

# --- Helpers to dynamically import ROS2 message types like "sensor_msgs/msg/BatteryState"
def import_msg_type(type_str: str):
    # e.g. "sensor_msgs/msg/BatteryState"
    try:
        pkg, _, name = type_str.partition('/msg/')
        if not _:
            raise ValueError(f'Invalid type string "{type_str}". Use "pkg/msg/TypeName".')
        module = __import__(f'{pkg}.msg', fromlist=[name])
        return getattr(module, name)
    except Exception as e:
        raise RuntimeError(f'Could not import message type "{type_str}": {e}')

def now_sec(node: Node) -> float:
    return node.get_clock().now().nanoseconds / 1e9

def age_str(age_s: Optional[float]) -> str:
    if age_s is None:
        return "—"
    if age_s < 1.0:  return f"{age_s*1000:.0f} ms"
    if age_s < 90.0: return f"{age_s:.1f} s"
    return f"{age_s/60:.1f} m"

def safe_get(msg: Any, path: str):
    """Get nested attribute by dotted path, e.g. 'orientation.x' or 'status.status'"""
    cur = msg
    for part in path.split('.'):
        if not hasattr(cur, part):
            return None
        cur = getattr(cur, part)
    return cur

@dataclass
class FieldSpec:
    label: str
    path: Optional[str] = None   # dotted path into message (e.g., "percentage")
    # optional computed—only for a few known keys (yaw_deg, rpy_deg, etc.)
    computed: Optional[str] = None
    fmt: str = "{}"             # format string

    def render(self, msg: Any) -> Tuple[str, str]:
        if msg is None:
            return (self.label, "—")
        try:
            if self.computed:
                val = compute_field(self.computed, msg)
            else:
                val = safe_get(msg, self.path) if self.path else None
            if val is None:
                out = "—"
            elif isinstance(val, float):
                out = self.fmt.format(val)
            else:
                out = self.fmt.format(val)
            return (self.label, out)
        except Exception:
            return (self.label, "—")

def quat_to_yaw_deg(qx, qy, qz, qw) -> float:
    # yaw (Z) from quaternion (ENU)
    siny_cosp = 2.0 * (qw*qz + qx*qy)
    cosy_cosp = 1.0 - 2.0 * (qy*qy + qz*qz)
    yaw = math.atan2(siny_cosp, cosy_cosp)
    return math.degrees(yaw)

def quat_to_rpy_deg(qx, qy, qz, qw) -> Tuple[float, float, float]:
    # roll (X), pitch (Y), yaw (Z), ENU
    sinr_cosp = 2.0 * (qw*qx + qy*qz)
    cosr_cosp = 1.0 - 2.0 * (qx*qx + qy*qy)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    sinp = 2.0 * (qw*qy - qz*qx)
    if abs(sinp) >= 1:
        pitch = math.copysign(math.pi/2, sinp)
    else:
        pitch = math.asin(sinp)

    siny_cosp = 2.0 * (qw*qz + qx*qy)
    cosy_cosp = 1.0 - 2.0 * (qy*qy + qz*qz)
    yaw = math.atan2(siny_cosp, cosy_cosp)
    return (math.degrees(roll), math.degrees(pitch), math.degrees(yaw))

def compute_field(key: str, msg: Any):
    if key == "yaw_deg":
        q = getattr(msg, "orientation", None)
        if q is None: return None
        return quat_to_yaw_deg(q.x, q.y, q.z, q.w)
    if key == "rpy_deg":
        q = getattr(msg, "orientation", None)
        if q is None: return None
        r, p, y = quat_to_rpy_deg(q.x, q.y, q.z, q.w)
        return f"R:{r:.1f}° P:{p:.1f}° Y:{y:.1f}°"
    if key == "ang_vel_norm":
        v = getattr(msg, "angular_velocity", None)
        if v is None: return None
        return math.sqrt(v.x*v.x + v.y*v.y + v.z*v.z)
    if key == "lin_acc_norm":
        a = getattr(msg, "linear_acceleration", None)
        if a is None: return None
        return math.sqrt(a.x*a.x + a.y*a.y + a.z*a.z)
    if key == "gps_accuracy":
        # Compute horizontal accuracy from position covariance
        cov = getattr(msg, "position_covariance", None)
        if cov is None or len(cov) < 5: return None
        # Horizontal accuracy is sqrt of average of x and y variances
        h_accuracy = math.sqrt((cov[0] + cov[4]) / 2.0)
        return h_accuracy
    if key == "rtk_status":
        # Decode GPS fix status into human-readable RTK status
        # Based on NavSatStatus constants and GPS quality mapping
        status = getattr(msg, "status", None)
        if status is None: return None
        status_code = getattr(status, "status", -1)
        # Map status codes to RTK-aware descriptions
        # STATUS_NO_FIX = -1, STATUS_FIX = 0, STATUS_SBAS_FIX = 1, STATUS_GBAS_FIX = 2
        if status_code == -1:
            return "No Fix"
        elif status_code == 0:
            return "GPS Fix"
        elif status_code == 1:
            return "DGPS/SBAS"
        elif status_code == 2:
            return "RTK Fix"
        else:
            return f"Unknown ({status_code})"
    return None

@dataclass
class SourceSpec:
    name: str
    topic: str
    type_str: str
    fields: List[FieldSpec] = field(default_factory=list)

class TopicWatcher:
    def __init__(self, node: Node, spec: SourceSpec):
        self.node = node
        self.spec = spec
        self.msg_type = import_msg_type(spec.type_str)
        qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10
        )
        self.last_msg: Optional[Any] = None
        self.last_t: Optional[float] = None
        self.sub = node.create_subscription(self.msg_type, spec.topic, self._cb, qos)

    def _cb(self, msg):
        self.last_msg = msg
        self.last_t   = now_sec(self.node)

    def snapshot(self) -> Tuple[Optional[Any], Optional[float]]:
        if self.last_msg is None:
            return (None, None)
        age = None
        if self.last_t is not None:
            age = max(0.0, now_sec(self.node) - self.last_t)
        return (self.last_msg, age)

class MultiTopicWatcher:
    """Watches multiple boolean topics and aggregates them into a single display"""
    def __init__(self, node: Node, name: str, topic_map: Dict[str, str]):
        self.node = node
        self.name = name
        self.topic_map = topic_map  # {label: topic_name}
        self.msg_type = import_msg_type("std_msgs/msg/Bool")
        qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=10
        )
        self.states: Dict[str, Optional[bool]] = {label: None for label in topic_map.keys()}
        self.last_t: Dict[str, Optional[float]] = {label: None for label in topic_map.keys()}
        self.subs = {}
        for label, topic in topic_map.items():
            self.subs[label] = node.create_subscription(
                self.msg_type, 
                topic, 
                lambda msg, l=label: self._cb(l, msg),
                qos
            )
    
    def _cb(self, label: str, msg):
        self.states[label] = msg.data
        self.last_t[label] = now_sec(self.node)
    
    def snapshot(self) -> Tuple[List[Tuple[str, str]], Optional[float]]:
        lines = []
        ages = []
        for label in self.topic_map.keys():
            state = self.states[label]
            if state is None:
                value = "—"
            else:
                value = "✓ ON" if state else "✗ OFF"
            lines.append((label, value))
            if self.last_t[label] is not None:
                ages.append(now_sec(self.node) - self.last_t[label])
        
        # Return the most recent update time
        age = min(ages) if ages else None
        return (lines, age)

class NodeStatusWatcher:
    """Watches for active ROS2 nodes"""
    def __init__(self, node: Node, node_patterns: Dict[str, str]):
        self.node = node
        self.node_patterns = node_patterns  # {label: node_name_pattern}
    
    def snapshot(self) -> List[Tuple[str, str]]:
        """Check which nodes are currently active"""
        node_names = self.node.get_node_names()
        lines = []
        for label, pattern in self.node_patterns.items():
            # Check if any node contains the pattern
            is_active = any(pattern in name for name in node_names)
            value = "✓ ACTIVE" if is_active else "✗ OFFLINE"
            lines.append((label, value))
        return lines

# --- Default panels: Mode, Features, Battery, GPS, IMU
def default_sources() -> List[SourceSpec]:
    return [
        SourceSpec(
            name="Robot Mode",
            topic="/robot_mode",
            type_str="std_msgs/msg/String",
            fields=[
                FieldSpec("Current", "data", "{}"),
            ],
        ),
        SourceSpec(
            name="Battery",
            topic="/battery_state",
            type_str="sensor_msgs/msg/BatteryState",
            fields=[
                FieldSpec("Voltage", "voltage", "{:.2f} V"),
                FieldSpec("Percentage", "percentage", "{:.1f} %"),
                FieldSpec("Current", "current", "{:.2f} A"),
            ],
        ),
        SourceSpec(
            name="GPS/RTK",
            topic="/gps/fix",
            type_str="sensor_msgs/msg/NavSatFix",
            fields=[
                FieldSpec("Latitude", "latitude", "{:.7f}"),
                FieldSpec("Longitude", "longitude", "{:.7f}"),
                FieldSpec("Altitude", "altitude", "{:.2f} m"),
                FieldSpec("RTK Status", computed="rtk_status"),
                FieldSpec("Accuracy", computed="gps_accuracy", fmt="{:.2f} m"),
            ],
        ),
        SourceSpec(
            name="IMU (MAVROS)",
            topic="/mavros/imu/data",
            type_str="sensor_msgs/msg/Imu",
            fields=[
                FieldSpec("Orientation", computed="rpy_deg"),
                FieldSpec("Angular Vel", computed="ang_vel_norm", fmt="{:.3f} rad/s"),
                FieldSpec("Linear Accel", computed="lin_acc_norm", fmt="{:.2f} m/s²"),
            ],
        ),

    ]

# --- YAML config (optional)
def load_yaml_config(path: str) -> List[SourceSpec]:
    import yaml
    with open(path, "r") as f:
        data = yaml.safe_load(f)
    specs: List[SourceSpec] = []
    for block in data or []:
        fields = []
        for fd in block.get("fields", []):
            fields.append(FieldSpec(
                label=fd.get("label", ""),
                path=fd.get("path"),
                computed=fd.get("computed"),
                fmt=fd.get("fmt", "{}"),
            ))
        specs.append(SourceSpec(
            name=block["name"],
            topic=block["topic"],
            type_str=block["type"],
            fields=fields
        ))
    return specs

def parse_extra_sources(args_list: List[str]) -> List[SourceSpec]:
    """
    --add name:topic:type:field1=path_or_comp,field2=...,fieldN=...
    Example:
      --add "WheelOdom:/wheel/odom:nav_msgs/msg/Odometry:speed=twist.twist.linear.x"
      --add "Temp:/temp:sensor_msgs/msg/Temperature:value=temperature"
    For computed fields, prefix with "c:" e.g. yaw=c:yaw_deg
    """
    extras = []
    for raw in args_list:
        try:
            name, topic, typestr, fields_str = raw.split(":", 3)
        except ValueError:
            print(f'Invalid --add spec "{raw}". Expected name:topic:type:fields', file=sys.stderr)
            continue
        fields = []
        for kv in fields_str.split(","):
            if not kv: continue
            if "=" not in kv:
                print(f'Invalid field "{kv}" (expected label=path_or_computed)', file=sys.stderr)
                continue
            label, rhs = kv.split("=", 1)
            if rhs.startswith("c:"):
                fields.append(FieldSpec(label=label, computed=rhs[2:], fmt="{}"))
            else:
                fields.append(FieldSpec(label=label, path=rhs, fmt="{}"))
        extras.append(SourceSpec(name=name, topic=topic, type_str=typestr, fields=fields))
    return extras

def clear_screen():
    if sys.stdout.isatty():
        print("\033[2J\033[H", end="")

def human_panel(name: str, age: Optional[float], lines: List[Tuple[str,str]]) -> str:
    header = f"[ {name} ]"
    age_part = f"(age {age_str(age)})" if age is not None else "(no data)"
    out = [f"{header} {age_part}"]
    for k, v in lines:
        out.append(f"  {k:<10} {v}")
    return "\n".join(out)

# ANSI color codes
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

def colorize_battery_voltage(voltage_str: str) -> str:
    """Color code battery voltage: green if >= 26.5V, red otherwise"""
    try:
        # Extract numeric value from string like "26.50 V"
        voltage = float(voltage_str.split()[0])
        if voltage >= 26.5:
            return f"{Colors.GREEN}{voltage_str}{Colors.RESET}"
        else:
            return f"{Colors.RED}{voltage_str}{Colors.RESET}"
    except (ValueError, IndexError):
        return voltage_str

def format_box(title: str, rows: List[Tuple[str, str]], age: Optional[float], width: int = 60) -> str:
    """Format data as a colored box with title and fields"""
    lines = []
    
    # Title bar with age
    age_text = age_str(age) if age is not None else "no data"
    title_text = f" {title} "
    age_display = f" ({age_text}) "
    padding = width - len(title_text) - len(age_display) - 2
    
    lines.append(f"┌{'─' * (width - 2)}┐")
    lines.append(f"│{Colors.CYAN}{Colors.BOLD}{title_text}{Colors.RESET}{' ' * padding}{Colors.DIM}{age_display}{Colors.RESET}│")
    lines.append(f"├{'─' * (width - 2)}┤")
    
    # Data rows
    if not rows:
        lines.append(f"│{Colors.DIM}  No data available{' ' * (width - 21)}{Colors.RESET}│")
    else:
        for label, value in rows:
            # Special handling for battery voltage
            if label == "Voltage" and "V" in value:
                value = colorize_battery_voltage(value)
            
            # Calculate padding to align to box width
            # Account for ANSI codes by using visible length
            visible_value = value
            for color in [Colors.RED, Colors.GREEN, Colors.YELLOW, Colors.CYAN, Colors.BOLD, Colors.DIM, Colors.RESET]:
                visible_value = visible_value.replace(color, "")
            
            label_part = f"  {label}:"
            padding_needed = width - len(label_part) - len(visible_value) - 3
            lines.append(f"│{label_part}{' ' * padding_needed}{value} │")
    
    lines.append(f"└{'─' * (width - 2)}┘")
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="ROS 2 CLI status page")
    parser.add_argument("--hz", type=float, default=2.0, help="Refresh rate (Hz)")
    parser.add_argument("--yaml", type=str, help="Optional YAML config with sources")
    parser.add_argument("--add", action="append", default=[],
                        help='Add a source inline: name:topic:type:field=path[,field=path...] '
                             '(use c:computed for computed fields, e.g. yaw=c:yaw_deg)')
    parser.add_argument("--no-defaults", action="store_true", help="Start empty (only YAML/--add)")
    parser.add_argument("--once", action="store_true", help="Print once and exit")
    args = parser.parse_args()

    rclpy.init()
    node = rclpy.create_node("ros_status_cli")

    sources: List[SourceSpec] = []
    if not args.no_defaults:
        sources.extend(default_sources())
    if args.yaml:
        try:
            sources.extend(load_yaml_config(args.yaml))
        except Exception as e:
            print(f"YAML load error: {e}", file=sys.stderr)
    if args.add:
        sources.extend(parse_extra_sources(args.add))

    if not sources:
        print("No sources configured. Use --add or --yaml. See --help.", file=sys.stderr)
        rclpy.shutdown()
        sys.exit(1)

    watchers = [TopicWatcher(node, s) for s in sources]
    
    # Add multi-topic watcher for features
    features_watcher = MultiTopicWatcher(node, "System Features", {
        "Motors": "/enable_motors",
        "Sensors": "/enable_sensors",
        "GPS": "/enable_gps",
        "LiDAR": "/enable_lidar",
        "Camera": "/enable_camera",
    })
    
    # Add node status watcher
    node_status_watcher = NodeStatusWatcher(node, {
        "Bridge": "bridge",
        "Camera": "camera",
        "MAVROS": "mavros",
        "Motor Ctrl": "motor_controller",
        "LiDAR": "sllidar",
        "GPS RTK": "gps_rtk",
        "IMU": "imu",
    })

    period = 1.0 / max(0.1, args.hz)
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.01)
            
            clear_screen()
            print(f"{Colors.CYAN}{Colors.BOLD}╔═══════════════════════════════════════════════════════════════╗{Colors.RESET}")
            print(f"{Colors.CYAN}{Colors.BOLD}║         ROS 2 MOWER STATUS — Ctrl+C to quit                  ║{Colors.RESET}")
            print(f"{Colors.CYAN}{Colors.BOLD}╚═══════════════════════════════════════════════════════════════╝{Colors.RESET}\n")
            
            # Node Status Box
            node_statuses = node_status_watcher.snapshot()
            if node_statuses:  # Only show if not empty
                node_rows = []
                for label, status in node_statuses:
                    # Color code status
                    if "ACTIVE" in status:
                        status = f"{Colors.GREEN}{status}{Colors.RESET}"
                    elif "OFFLINE" in status:
                        status = f"{Colors.RED}{status}{Colors.RESET}"
                    node_rows.append((label, status))
                print(format_box("Node Status", node_rows, None))
                print()
            
            # System Features Box
            feature_lines, feature_age = features_watcher.snapshot()
            if feature_lines:  # Only show if not empty
                feature_rows = []
                for label, status in feature_lines:
                    # Color code enabled/disabled
                    if "✓ ON" in status:
                        status = f"{Colors.GREEN}{status}{Colors.RESET}"
                    elif "✗ OFF" in status:
                        status = f"{Colors.DIM}{status}{Colors.RESET}"
                    feature_rows.append((label, status))
                print(format_box("System Features", feature_rows, feature_age))
                print()
            
            # Regular watchers - each in its own box
            for w in watchers:
                msg, age = w.snapshot()
                
                # Skip empty topics
                if msg is None:
                    continue
                
                # Render all fields for this topic
                field_rows = []
                for f in w.spec.fields:
                    label, value = f.render(msg)
                    if value != "—":  # Only show non-empty values
                        field_rows.append((label, value))
                
                # Only display box if there are non-empty fields
                if field_rows:
                    print(format_box(w.spec.name, field_rows, age))
                    print()
            
            if args.once:
                break
            time.sleep(period)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == "__main__":
    main()
