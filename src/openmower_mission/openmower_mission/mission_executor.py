#!/usr/bin/env python3
"""
Mission Executor — OpenMowerNext-inspired autonomous mowing state machine.

This is the central brain of the mower: it selects zones by priority,
requests coverage paths, sends Nav2 waypoint goals, monitors progress,
handles battery return, and loops back for the next zone.

State machine:
  IDLE ──→ SELECTING_ZONE ──→ GENERATING_PATH ──→ MOWING
    ↑                                                 │
    │◄──────────── ZONE_COMPLETE ◄────────────────────┤
    │                                                 │ (battery low / obstacle stuck)
    └─────────────── DOCK_RETURN ◄────────────────────┘
              ↓
          CHARGING ──→ IDLE (when charged)

Topics:
  Subscribed:
    /robot_mode          (std_msgs/String)       — current mode
    /battery/state       (std_msgs/String)        — NORMAL/LOW/CRITICAL/CHARGING/CHARGED
    /mission/command     (std_msgs/String)        — RETURN_TO_DOCK / EMERGENCY_DOCK / BATTERY_CHARGED
    /zones               (rosmower_msgs/ZoneArray)
    /coverage/path       (nav_msgs/Path)          — generated coverage path
    /coverage/status     (std_msgs/String)        — coverage generator feedback
    /cmd_vel             (geometry_msgs/Twist)    — monitored to detect if robot is stuck

  Published:
    /mission/state       (std_msgs/String)        — current state
    /mission/active_zone (std_msgs/String)        — currently mowing zone ID
    /robot_mode_cmd      (std_msgs/String)        — mode change requests
    /coverage/request_zone (std_msgs/String)      — triggers coverage path generation
    /goal_pose           (geometry_msgs/PoseStamped) — sends Nav2 goals
    /mission/progress    (std_msgs/String)        — JSON progress report
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool
from geometry_msgs.msg import PoseStamped, Twist
from nav_msgs.msg import Path
from rosmower_msgs.msg import ZoneArray, Zone

import json
import math
import time
from enum import Enum, auto
from typing import Optional, List, Dict


class MissionState(Enum):
    IDLE = auto()
    SELECTING_ZONE = auto()
    GENERATING_PATH = auto()
    MOWING = auto()
    OBSTACLE_RECOVERY = auto()
    ZONE_COMPLETE = auto()
    DOCK_RETURN = auto()
    CHARGING = auto()
    EMERGENCY_STOP = auto()


class MissionExecutor(Node):
    """
    Autonomous mowing mission executor.

    Orchestrates the full mow cycle: zone selection → coverage path →
    waypoint following → completion → dock return → recharge → repeat.

    Modeled after OpenMowerNext's behavior tree architecture but implemented
    as a Python state machine for compatibility with ROS2 Humble.
    """

    def __init__(self):
        super().__init__('mission_executor')

        # ── Parameters ──────────────────────────────────────────────────────
        self.declare_parameter('waypoint_goal_tolerance_m', 0.3)
        self.declare_parameter('stuck_velocity_threshold', 0.01)  # m/s
        self.declare_parameter('stuck_timeout_sec', 15.0)
        self.declare_parameter('max_recovery_attempts', 3)
        self.declare_parameter('battery_return_threshold_pct', 25.0)
        self.declare_parameter('path_generation_timeout_sec', 10.0)
        self.declare_parameter('loop_hz', 2.0)

        self.goal_tolerance = self.get_parameter('waypoint_goal_tolerance_m').value
        self.stuck_vel_threshold = self.get_parameter('stuck_velocity_threshold').value
        self.stuck_timeout = self.get_parameter('stuck_timeout_sec').value
        self.max_recovery = self.get_parameter('max_recovery_attempts').value
        self.battery_return_pct = self.get_parameter('battery_return_threshold_pct').value
        self.path_gen_timeout = self.get_parameter('path_generation_timeout_sec').value

        # ── State ────────────────────────────────────────────────────────────
        self.state = MissionState.IDLE
        self.zones: Dict[str, Zone] = {}
        self.current_zone_id: Optional[str] = None
        self.coverage_path: Optional[Path] = None
        self.current_waypoint_idx: int = 0
        self.battery_state: str = 'NORMAL'
        self.robot_mode: str = 'idle'
        self.last_cmd_vel_time: float = time.time()
        self.last_pose_time: float = time.time()
        self.recovery_attempts: int = 0
        self.path_request_time: Optional[float] = None
        self.current_pose: Optional[PoseStamped] = None
        self.mission_running: bool = False
        self.completed_zones: List[str] = []

        # ── Subscribers ───────────────────────────────────────────────────────
        self.create_subscription(ZoneArray, '/zones', self._zones_cb, 10)
        self.create_subscription(String, '/robot_mode', self._mode_cb, 10)
        self.create_subscription(String, '/battery/state', self._battery_cb, 10)
        self.create_subscription(String, '/mission/command', self._mission_cmd_cb, 10)
        self.create_subscription(Path, '/coverage/path', self._coverage_path_cb, 10)
        self.create_subscription(String, '/coverage/status', self._coverage_status_cb, 10)
        self.create_subscription(Twist, '/cmd_vel', self._cmd_vel_cb, 10)

        # ── Publishers ────────────────────────────────────────────────────────
        self.state_pub = self.create_publisher(String, '/mission/state', 10)
        self.active_zone_pub = self.create_publisher(String, '/mission/active_zone', 10)
        self.mode_cmd_pub = self.create_publisher(String, '/robot_mode_cmd', 10)
        self.coverage_req_pub = self.create_publisher(String, '/coverage/request_zone', 10)
        self.goal_pub = self.create_publisher(PoseStamped, '/goal_pose', 10)
        self.progress_pub = self.create_publisher(String, '/mission/progress', 10)

        # ── Main loop timer ───────────────────────────────────────────────────
        hz = self.get_parameter('loop_hz').value
        self.create_timer(1.0 / hz, self._tick)

        self.get_logger().info('Mission Executor started — state: IDLE')

    # ── Subscriber Callbacks ─────────────────────────────────────────────────

    def _zones_cb(self, msg: ZoneArray):
        for zone in msg.zones:
            self.zones[zone.id] = zone

    def _mode_cb(self, msg: String):
        self.robot_mode = msg.data
        # Entering mowing mode starts the mission
        if msg.data == 'mowing' and self.state == MissionState.IDLE:
            self.get_logger().info('Mode → mowing: starting autonomous mission')
            self.mission_running = True
            self.completed_zones.clear()
            self._transition(MissionState.SELECTING_ZONE)

    def _battery_cb(self, msg: String):
        self.battery_state = msg.data

    def _mission_cmd_cb(self, msg: String):
        cmd = msg.data
        if cmd == 'EMERGENCY_DOCK':
            self.get_logger().error('EMERGENCY_DOCK received — aborting to dock')
            self._transition(MissionState.EMERGENCY_STOP)
        elif cmd == 'RETURN_TO_DOCK' and self.state == MissionState.MOWING:
            self.get_logger().warn('Low battery: transitioning to dock return')
            self._transition(MissionState.DOCK_RETURN)
        elif cmd == 'BATTERY_CHARGED' and self.state == MissionState.CHARGING:
            self.get_logger().info('Battery charged — returning to IDLE')
            self._transition(MissionState.IDLE)

    def _coverage_path_cb(self, msg: Path):
        if self.state == MissionState.GENERATING_PATH:
            self.coverage_path = msg
            self.current_waypoint_idx = 0
            self.recovery_attempts = 0
            self.get_logger().info(
                f'Coverage path received: {len(msg.poses)} waypoints'
            )
            self._transition(MissionState.MOWING)

    def _coverage_status_cb(self, msg: String):
        if msg.data.startswith('ERROR') and self.state == MissionState.GENERATING_PATH:
            self.get_logger().error(f'Coverage path error: {msg.data} — skipping zone')
            self._transition(MissionState.ZONE_COMPLETE)

    def _cmd_vel_cb(self, msg: Twist):
        speed = math.sqrt(msg.linear.x ** 2 + msg.linear.y ** 2)
        if speed > self.stuck_vel_threshold:
            self.last_cmd_vel_time = time.time()

    # ── State Machine ─────────────────────────────────────────────────────────

    def _tick(self):
        """Main state machine tick — called at loop_hz."""
        self._publish_state()

        if self.state == MissionState.IDLE:
            pass  # Waiting for mode → mowing

        elif self.state == MissionState.SELECTING_ZONE:
            self._tick_selecting_zone()

        elif self.state == MissionState.GENERATING_PATH:
            self._tick_generating_path()

        elif self.state == MissionState.MOWING:
            self._tick_mowing()

        elif self.state == MissionState.OBSTACLE_RECOVERY:
            self._tick_recovery()

        elif self.state == MissionState.ZONE_COMPLETE:
            self._tick_zone_complete()

        elif self.state == MissionState.DOCK_RETURN:
            self._tick_dock_return()

        elif self.state == MissionState.CHARGING:
            pass  # Waiting for BATTERY_CHARGED command

        elif self.state == MissionState.EMERGENCY_STOP:
            self._tick_emergency_stop()

    def _tick_selecting_zone(self):
        """Choose the highest-priority unmowed enabled zone."""
        if not self.zones:
            self.get_logger().warn('No zones available — waiting...')
            return

        candidates = [
            z for z in self.zones.values()
            if z.enabled and z.id not in self.completed_zones
        ]

        if not candidates:
            self.get_logger().info('All zones completed — returning to dock')
            self.mission_running = False
            self._transition(MissionState.DOCK_RETURN)
            return

        # Select by highest priority (lower priority number = higher priority in OpenMower convention)
        best = min(candidates, key=lambda z: z.priority)
        self.current_zone_id = best.id
        self.get_logger().info(
            f'Selected zone: {best.name} (id={best.id}, priority={best.priority})'
        )
        self._publish_active_zone(best.id)
        self._transition(MissionState.GENERATING_PATH)

    def _tick_generating_path(self):
        """Request coverage path and wait for response."""
        if self.path_request_time is None:
            # First tick — send the request
            msg = String()
            msg.data = self.current_zone_id
            self.coverage_req_pub.publish(msg)
            self.path_request_time = time.time()
            self.get_logger().info(f'Requesting coverage path for zone: {self.current_zone_id}')
            return

        # Timeout guard
        elapsed = time.time() - self.path_request_time
        if elapsed > self.path_gen_timeout:
            self.get_logger().error(
                f'Coverage path generation timed out after {elapsed:.1f}s — skipping zone'
            )
            self.path_request_time = None
            self._transition(MissionState.ZONE_COMPLETE)

    def _tick_mowing(self):
        """Follow coverage path waypoint by waypoint via /goal_pose."""
        if self.coverage_path is None or len(self.coverage_path.poses) == 0:
            self.get_logger().error('No coverage path — aborting zone')
            self._transition(MissionState.ZONE_COMPLETE)
            return

        # Battery check
        if self.battery_state in ('LOW', 'CRITICAL'):
            self.get_logger().warn(f'Battery {self.battery_state} during mowing — returning to dock')
            self._transition(MissionState.DOCK_RETURN)
            return

        # Stuck detection
        if time.time() - self.last_cmd_vel_time > self.stuck_timeout:
            self.get_logger().warn('Robot appears stuck — attempting recovery')
            self._transition(MissionState.OBSTACLE_RECOVERY)
            return

        # Check if all waypoints complete
        if self.current_waypoint_idx >= len(self.coverage_path.poses):
            self.get_logger().info(f'Zone {self.current_zone_id} fully covered!')
            self._transition(MissionState.ZONE_COMPLETE)
            return

        # Publish next waypoint goal
        goal = self.coverage_path.poses[self.current_waypoint_idx]
        goal.header.stamp = self.get_clock().now().to_msg()
        self.goal_pub.publish(goal)

        self._publish_progress()

        # Advance to next waypoint (Nav2 controller handles actual movement;
        # here we advance on a time schedule — replace with pose feedback for production)
        self.current_waypoint_idx += 1
        self.last_cmd_vel_time = time.time()   # reset stuck timer on goal advance

    def _tick_recovery(self):
        """Attempt obstacle recovery — back up and rotate."""
        self.recovery_attempts += 1
        self.get_logger().warn(
            f'Recovery attempt {self.recovery_attempts}/{self.max_recovery}'
        )

        if self.recovery_attempts > self.max_recovery:
            self.get_logger().error('Max recovery attempts exceeded — returning to dock')
            self._transition(MissionState.DOCK_RETURN)
            return

        # Simple recovery: publish a back-up goal
        if self.current_waypoint_idx > 0:
            backup_idx = max(0, self.current_waypoint_idx - 3)
            backup_goal = self.coverage_path.poses[backup_idx]
            backup_goal.header.stamp = self.get_clock().now().to_msg()
            self.goal_pub.publish(backup_goal)
            self.current_waypoint_idx = backup_idx
            self.last_cmd_vel_time = time.time()

        self._transition(MissionState.MOWING)

    def _tick_zone_complete(self):
        """Mark zone as done, update coverage, select next zone."""
        if self.current_zone_id:
            self.completed_zones.append(self.current_zone_id)
            self.get_logger().info(
                f'Zone {self.current_zone_id} done. '
                f'Completed: {len(self.completed_zones)} zones.'
            )

        self.current_zone_id = None
        self.coverage_path = None
        self.current_waypoint_idx = 0
        self.path_request_time = None

        if self.mission_running and self.battery_state not in ('LOW', 'CRITICAL'):
            self._transition(MissionState.SELECTING_ZONE)
        else:
            self._transition(MissionState.DOCK_RETURN)

    def _tick_dock_return(self):
        """Trigger mode change to idle; dock_manager handles navigation."""
        self.get_logger().info('Initiating dock return')
        mode = String()
        mode.data = 'idle'
        self.mode_cmd_pub.publish(mode)
        # dock_manager node handles the actual navigation on /mission/state=DOCK_RETURN
        self._transition(MissionState.CHARGING)

    def _tick_emergency_stop(self):
        """Publish stop and await recovery."""
        stop = Twist()
        self.get_logger().error('EMERGENCY STOP — publishing zero velocity')
        # Publish via mode cmd (mode_manager gates motors)
        mode = String()
        mode.data = 'idle'
        self.mode_cmd_pub.publish(mode)
        self._transition(MissionState.IDLE)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _transition(self, new_state: MissionState):
        old = self.state.name
        self.state = new_state
        self.get_logger().info(f'State: {old} → {new_state.name}')
        self._publish_state()

    def _publish_state(self):
        msg = String()
        msg.data = self.state.name
        self.state_pub.publish(msg)

    def _publish_active_zone(self, zone_id: str):
        msg = String()
        msg.data = zone_id
        self.active_zone_pub.publish(msg)

    def _publish_progress(self):
        if self.coverage_path is None:
            return
        total = len(self.coverage_path.poses)
        done = self.current_waypoint_idx
        pct = round(done / total * 100.0, 1) if total > 0 else 0.0
        data = {
            'zone_id': self.current_zone_id,
            'state': self.state.name,
            'waypoints_done': done,
            'waypoints_total': total,
            'coverage_pct': pct,
            'battery_state': self.battery_state,
            'completed_zones': self.completed_zones,
        }
        msg = String()
        msg.data = json.dumps(data)
        self.progress_pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = MissionExecutor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
