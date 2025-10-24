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

# --- Default panels: Battery, GPS, IMU
def default_sources() -> List[SourceSpec]:
    return [
        SourceSpec(
            name="Battery",
            topic="/mavros/battery",
            type_str="sensor_msgs/msg/BatteryState",
            fields=[
            ],
        ),
        SourceSpec(
            name="GPS",
            topic="/fix",
            type_str="sensor_msgs/msg/NavSatFix",
            fields=[
                FieldSpec("Lat", "latitude", "{:.6f}"),
                FieldSpec("Lon", "longitude", "{:.6f}"),
                FieldSpec("Alt", "altitude", "{:.2f} m"),
                FieldSpec("Status", "status.status", "{}"),
            ],
        ),
        SourceSpec(
            name="IMU",
            topic="/imu",
            type_str="sensor_msgs/msg/Imu",
            fields=[
                FieldSpec("Yaw", computed="yaw_deg", fmt="{:.1f} °"),
                FieldSpec("RPY", computed="rpy_deg", fmt="{}"),
                FieldSpec("|ω|", computed="ang_vel_norm", fmt="{:.3f} rad/s"),
                FieldSpec("|a|", computed="lin_acc_norm", fmt="{:.3f} m/s²"),
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

    period = 1.0 / max(0.1, args.hz)
    try:
        while rclpy.ok():
            rclpy.spin_once(node, timeout_sec=0.01)
            panels = []
            for w in watchers:
                msg, age = w.snapshot()
                # Build lines
                lines: List[Tuple[str,str]] = []
                if msg is None:
                    panels.append(human_panel(w.spec.name, None, []))
                    continue
                for f in w.spec.fields:
                    lines.append(f.render(msg))
                panels.append(human_panel(w.spec.name, age, lines))

            clear_screen()
            print("ROS 2 Status (CLI) — Ctrl+C to quit\n")
            print("\n\n".join(panels))
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
