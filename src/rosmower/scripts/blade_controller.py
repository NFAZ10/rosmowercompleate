#!/usr/bin/env python3

from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Optional

import rclpy
from mavros_msgs.srv import CommandLong
from rclpy.node import Node
from std_msgs.msg import Float32, Int16MultiArray, UInt16


MAV_CMD_DO_SET_SERVO = 183


@dataclass
class ServoTarget:
    channel: int
    pwm: int


@dataclass
class CommandGroup:
    label: str
    commands: List[ServoTarget]
    height_percent: Optional[float] = None
    motor_pwm: Optional[int] = None
    left_trim_pwm: Optional[int] = None
    right_trim_pwm: Optional[int] = None
    inter_command_delay_sec: float = 0.0
    publish_motor_state_each_step: bool = False
    delays_after_commands: Optional[List[float]] = None


class BladeController(Node):
    def __init__(self) -> None:
        super().__init__('blade_controller')

        self.declare_parameter('command_service', '/mavros/cmd/command')
        self.declare_parameter('blade_motor_channel', 1)
        self.declare_parameter('blade_motor_min_pwm', 1000)
        self.declare_parameter('blade_motor_min_running_pwm', 1500)
        self.declare_parameter('blade_motor_max_pwm', 3000)
        self.declare_parameter('blade_motor_stop_pwm', 1000)
        self.declare_parameter('blade_motor_start_pop_pwm', 2000)
        self.declare_parameter('blade_motor_start_pop_duration_sec', 0.15)
        self.declare_parameter('blade_motor_ramp_step_pwm', 100)
        self.declare_parameter('blade_motor_ramp_interval_sec', 0.1)
        self.declare_parameter('blade_height_spin_lock_percent', 100.0)
        self.declare_parameter('height_ramp_step_percent', 5.0)
        self.declare_parameter('height_ramp_interval_sec', 0.1)
        self.declare_parameter('height_servo_left_trim_pwm', 0)
        self.declare_parameter('height_servo_right_trim_pwm', 0)
        self.declare_parameter('height_servo_trim_min_pwm', -300)
        self.declare_parameter('height_servo_trim_max_pwm', 300)
        self.declare_parameter('height_servo_left_channel', 6)
        self.declare_parameter('height_servo_right_channel', 7)
        self.declare_parameter('height_servo_left_high_pwm', 1650)
        self.declare_parameter('height_servo_left_low_pwm', 1000)
        self.declare_parameter('height_servo_right_high_pwm', 1000)
        self.declare_parameter('height_servo_right_low_pwm', 1650)
        self.declare_parameter('default_height_percent', 100.0)

        self.command_service = self.get_parameter('command_service').value
        self.blade_motor_channel = int(self.get_parameter('blade_motor_channel').value)
        self.blade_motor_min_pwm = int(self.get_parameter('blade_motor_min_pwm').value)
        self.blade_motor_stop_pwm = int(self.get_parameter('blade_motor_stop_pwm').value)
        self.blade_motor_min_running_pwm = max(
            self.blade_motor_stop_pwm,
            int(self.get_parameter('blade_motor_min_running_pwm').value),
        )
        self.blade_motor_max_pwm = max(
            self.blade_motor_min_running_pwm,
            int(self.get_parameter('blade_motor_max_pwm').value),
        )
        self.blade_motor_start_pop_pwm = max(
            self.blade_motor_min_running_pwm,
            min(
                self.blade_motor_max_pwm,
                int(self.get_parameter('blade_motor_start_pop_pwm').value),
            ),
        )
        self.blade_motor_start_pop_duration_sec = max(
            0.0,
            float(self.get_parameter('blade_motor_start_pop_duration_sec').value),
        )
        self.blade_motor_ramp_step_pwm = max(
            1,
            int(self.get_parameter('blade_motor_ramp_step_pwm').value),
        )
        self.blade_motor_ramp_interval_sec = max(
            0.0,
            float(self.get_parameter('blade_motor_ramp_interval_sec').value),
        )
        self.blade_height_spin_lock_percent = max(
            0.0,
            min(100.0, float(self.get_parameter('blade_height_spin_lock_percent').value)),
        )
        self.height_ramp_step_percent = max(
            0.1,
            float(self.get_parameter('height_ramp_step_percent').value),
        )
        self.height_ramp_interval_sec = max(
            0.0,
            float(self.get_parameter('height_ramp_interval_sec').value),
        )
        raw_trim_min = int(self.get_parameter('height_servo_trim_min_pwm').value)
        raw_trim_max = int(self.get_parameter('height_servo_trim_max_pwm').value)
        self.height_servo_trim_min_pwm = min(raw_trim_min, raw_trim_max)
        self.height_servo_trim_max_pwm = max(raw_trim_min, raw_trim_max)
        self.height_servo_left_channel = int(self.get_parameter('height_servo_left_channel').value)
        self.height_servo_right_channel = int(self.get_parameter('height_servo_right_channel').value)
        self.height_servo_left_high_pwm = int(self.get_parameter('height_servo_left_high_pwm').value)
        self.height_servo_left_low_pwm = int(self.get_parameter('height_servo_left_low_pwm').value)
        self.height_servo_right_high_pwm = int(self.get_parameter('height_servo_right_high_pwm').value)
        self.height_servo_right_low_pwm = int(self.get_parameter('height_servo_right_low_pwm').value)
        self.current_left_trim_pwm = self._clamp_int(
            int(self.get_parameter('height_servo_left_trim_pwm').value),
            self.height_servo_trim_min_pwm,
            self.height_servo_trim_max_pwm,
            'left servo trim pwm',
        )
        self.current_right_trim_pwm = self._clamp_int(
            int(self.get_parameter('height_servo_right_trim_pwm').value),
            self.height_servo_trim_min_pwm,
            self.height_servo_trim_max_pwm,
            'right servo trim pwm',
        )
        self.current_height_percent = float(self.get_parameter('default_height_percent').value)
        self.current_motor_pwm = self.blade_motor_stop_pwm
        self.current_left_pwm, self.current_right_pwm = self._height_percent_to_pwm(self.current_height_percent)

        self.command_client = self.create_client(CommandLong, self.command_service)
        self.pending_groups: Deque[CommandGroup] = deque()
        self.active_group: Optional[CommandGroup] = None
        self.active_command_index = 0
        self.command_in_flight = False
        self.last_service_warning_ns = 0
        self.next_command_time_ns = 0

        self.height_cmd_sub = self.create_subscription(
            Float32,
            '/blade/height_percent_cmd',
            self.height_command_callback,
            10,
        )
        self.motor_cmd_sub = self.create_subscription(
            UInt16,
            '/blade/motor_pwm_cmd',
            self.motor_command_callback,
            10,
        )
        self.trim_cmd_sub = self.create_subscription(
            Int16MultiArray,
            '/blade/height_servo_trim_pwm_cmd',
            self.trim_command_callback,
            10,
        )

        self.height_state_pub = self.create_publisher(Float32, '/blade/height_percent', 10)
        self.motor_state_pub = self.create_publisher(UInt16, '/blade/motor_pwm', 10)
        self.left_pwm_pub = self.create_publisher(UInt16, '/blade/servo6_pwm', 10)
        self.right_pwm_pub = self.create_publisher(UInt16, '/blade/servo7_pwm', 10)
        self.trim_state_pub = self.create_publisher(Int16MultiArray, '/blade/height_servo_trim_pwm', 10)

        self.create_timer(0.05, self.process_queue)
        self.create_timer(1.0, self.publish_state)

        self.get_logger().info(
            'Blade controller ready: servo 1 = blade motor PWM, '
            'servo 6/7 = synchronized blade height via MAVROS command_long'
        )
        self.get_logger().info(
            f'Blade motor PWM range: {self.blade_motor_min_running_pwm}-{self.blade_motor_max_pwm}, '
            f'stop={self.blade_motor_stop_pwm}'
        )
        self.get_logger().info(
            f'Blade motor ramp: step={self.blade_motor_ramp_step_pwm} pwm, '
            f'interval={self.blade_motor_ramp_interval_sec:.2f}s'
        )
        self.get_logger().info(
            f'Blade motor start pop: pwm={self.blade_motor_start_pop_pwm}, '
            f'duration={self.blade_motor_start_pop_duration_sec:.2f}s'
        )
        self.get_logger().info(
            f'Blade height ramp: step={self.height_ramp_step_percent:.1f}%, '
            f'interval={self.height_ramp_interval_sec:.2f}s, '
            f'spin lock at {self.blade_height_spin_lock_percent:.1f}%'
        )
        self.get_logger().info(
            f'Blade height defaults: {self.current_height_percent:.1f}% '
            f'(servo 6 {self.current_left_pwm}, servo 7 {self.current_right_pwm})'
        )
        self.get_logger().info(
            f'Blade height trims: left={self.current_left_trim_pwm}, '
            f'right={self.current_right_trim_pwm}'
        )

    def height_command_callback(self, msg: Float32) -> None:
        height_percent = self._clamp_float(msg.data, 0.0, 100.0, 'blade height percent')
        target_left_pwm, target_right_pwm = self._height_percent_to_pwm(height_percent)

        if (
            height_percent >= self.blade_height_spin_lock_percent
            and self.current_motor_pwm > self.blade_motor_stop_pwm
        ):
            self.pending_groups.append(
                self._make_motor_command_group(
                    self.blade_motor_stop_pwm,
                    'blade motor stop for top height',
                )
            )
            self.get_logger().warn(
                'Requested highest blade height while blade is spinning; '
                'stopping blade motor first'
            )

        self.pending_groups.append(
            CommandGroup(
                label=f'blade height {height_percent:.1f}%',
                commands=[],
                height_percent=height_percent,
            )
        )
        self.get_logger().info(
            f'Queued blade height {height_percent:.1f}% '
            f'(servo {self.height_servo_left_channel}={target_left_pwm}, '
            f'servo {self.height_servo_right_channel}={target_right_pwm})'
        )

    def motor_command_callback(self, msg: UInt16) -> None:
        if self._is_height_spin_locked():
            if int(msg.data) > self.blade_motor_stop_pwm:
                self.get_logger().warn(
                    'Blade motor command rejected because blade height is at the highest position'
                )
                if self.current_motor_pwm > self.blade_motor_stop_pwm:
                    self.pending_groups.appendleft(
                        self._make_motor_command_group(
                            self.blade_motor_stop_pwm,
                            'blade motor stop due to top height lock',
                        )
                    )
                self.publish_state()
                return

        pwm = self._normalize_motor_target_pwm(int(msg.data))
        motor_group = self._make_motor_command_group(pwm)
        self.pending_groups.append(motor_group)
        self.get_logger().info(
            f'Queued {motor_group.label} on servo {self.blade_motor_channel}'
        )

    def trim_command_callback(self, msg: Int16MultiArray) -> None:
        if len(msg.data) < 2:
            self.get_logger().error(
                'Servo trim command requires two values: [left_trim_pwm, right_trim_pwm]'
            )
            return

        left_trim_pwm = self._clamp_int(
            int(msg.data[0]),
            self.height_servo_trim_min_pwm,
            self.height_servo_trim_max_pwm,
            'left servo trim pwm',
        )
        right_trim_pwm = self._clamp_int(
            int(msg.data[1]),
            self.height_servo_trim_min_pwm,
            self.height_servo_trim_max_pwm,
            'right servo trim pwm',
        )

        self.pending_groups.append(
            CommandGroup(
                label=f'blade servo trim L={left_trim_pwm} R={right_trim_pwm}',
                commands=[],
                left_trim_pwm=left_trim_pwm,
                right_trim_pwm=right_trim_pwm,
            )
        )
        self.get_logger().info(
            f'Queued blade servo trim update: left={left_trim_pwm}, right={right_trim_pwm}'
        )

    def process_queue(self) -> None:
        if self.active_group is None and not self.pending_groups:
            return

        if not self.command_client.wait_for_service(timeout_sec=0.0):
            now_ns = self.get_clock().now().nanoseconds
            if now_ns - self.last_service_warning_ns > 5_000_000_000:
                self.last_service_warning_ns = now_ns
                self.get_logger().warn(
                    f'Waiting for MAVROS service {self.command_service} '
                    'before applying blade commands'
                )
            return

        if self.command_in_flight:
            return

        now_ns = self.get_clock().now().nanoseconds
        if self.active_group is None:
            self.active_group = self.pending_groups.popleft()
            self._prepare_group(self.active_group)
            self.active_command_index = 0
            self.next_command_time_ns = now_ns
            self.get_logger().info(
                f'Applying {self.active_group.label} '
                f'({len(self.active_group.commands)} step(s))'
            )

        if now_ns < self.next_command_time_ns:
            return

        self._send_active_command()

    def _prepare_group(self, group: CommandGroup) -> None:
        if group.commands:
            return

        if group.motor_pwm is not None:
            commands, delays_after_commands = self._build_motor_command_sequence(group.motor_pwm)
            group.commands = commands
            group.delays_after_commands = delays_after_commands
            group.inter_command_delay_sec = (
                self.blade_motor_ramp_interval_sec if len(commands) > 1 else 0.0
            )
            group.publish_motor_state_each_step = True
            return

        if group.height_percent is not None:
            commands, delays_after_commands = self._build_height_ramp_commands(group.height_percent)
            group.commands = commands
            group.delays_after_commands = delays_after_commands
            return

        if group.left_trim_pwm is not None and group.right_trim_pwm is not None:
            target_left_pwm, target_right_pwm = self._height_percent_to_pwm(
                self.current_height_percent,
                left_trim_pwm=group.left_trim_pwm,
                right_trim_pwm=group.right_trim_pwm,
            )
            commands, delays_after_commands = self._build_servo_pair_ramp_commands(
                target_left_pwm,
                target_right_pwm,
            )
            group.commands = commands
            group.delays_after_commands = delays_after_commands
            return

        raise RuntimeError(f'Command group "{group.label}" has no executable targets')

    def _send_active_command(self) -> None:
        if self.active_group is None:
            return

        target = self.active_group.commands[self.active_command_index]
        self.command_in_flight = True
        request = CommandLong.Request()
        request.broadcast = False
        request.command = MAV_CMD_DO_SET_SERVO
        request.confirmation = 0
        request.param1 = float(target.channel)
        request.param2 = float(target.pwm)
        request.param3 = 0.0
        request.param4 = 0.0
        request.param5 = 0.0
        request.param6 = 0.0
        request.param7 = 0.0

        future = self.command_client.call_async(request)
        future.add_done_callback(
            lambda future_result, expected=target: self._handle_command_response(
                future_result,
                expected,
            )
        )

    def _handle_command_response(self, future, expected: ServoTarget) -> None:
        self.command_in_flight = False
        active_group = self.active_group
        if active_group is None:
            return

        try:
            response = future.result()
        except Exception as exc:
            self.get_logger().error(
                f'Failed to apply {active_group.label} on servo {expected.channel}: {exc}'
            )
            self.active_group = None
            self.active_command_index = 0
            self.next_command_time_ns = 0
            return

        if not response.success:
            self.get_logger().error(
                f'MAVROS rejected {active_group.label} on servo {expected.channel} '
                f'(result={response.result})'
            )
            self.active_group = None
            self.active_command_index = 0
            self.next_command_time_ns = 0
            return

        if expected.channel == self.height_servo_left_channel:
            self.current_left_pwm = expected.pwm
            self.publish_state()
        elif expected.channel == self.height_servo_right_channel:
            self.current_right_pwm = expected.pwm
            self.publish_state()

        if active_group.publish_motor_state_each_step and expected.channel == self.blade_motor_channel:
            self.current_motor_pwm = expected.pwm
            self.publish_state()

        self.active_command_index += 1
        if self.active_group is None:
            return

        if self.active_command_index < len(self.active_group.commands):
            executed_index = self.active_command_index - 1
            delay_sec = active_group.inter_command_delay_sec
            if (
                active_group.delays_after_commands is not None
                and executed_index < len(active_group.delays_after_commands)
            ):
                delay_sec = active_group.delays_after_commands[executed_index]

            delay_ns = int(delay_sec * 1_000_000_000)
            self.next_command_time_ns = self.get_clock().now().nanoseconds + delay_ns
            return

        finished_group = self.active_group
        self.active_group = None
        self.active_command_index = 0
        self.next_command_time_ns = 0
        self._commit_group(finished_group)

    def _commit_group(self, group: CommandGroup) -> None:
        if group.height_percent is not None:
            self.current_height_percent = group.height_percent
            self.current_left_pwm, self.current_right_pwm = self._height_percent_to_pwm(
                self.current_height_percent
            )

            if (
                self.current_height_percent >= self.blade_height_spin_lock_percent
                and self.current_motor_pwm > self.blade_motor_stop_pwm
            ):
                self.pending_groups.appendleft(
                    self._make_motor_command_group(
                        self.blade_motor_stop_pwm,
                        'blade motor stop due to top height lock',
                    )
                )
                self.get_logger().warn(
                    'Blade height reached the highest position; scheduling blade motor stop'
                )

        if group.motor_pwm is not None:
            self.current_motor_pwm = group.motor_pwm

        if group.left_trim_pwm is not None:
            self.current_left_trim_pwm = group.left_trim_pwm

        if group.right_trim_pwm is not None:
            self.current_right_trim_pwm = group.right_trim_pwm

        self.publish_state()
        self.get_logger().info(f'Applied {group.label}')

    def publish_state(self) -> None:
        height_msg = Float32()
        height_msg.data = float(self.current_height_percent)
        self.height_state_pub.publish(height_msg)

        motor_msg = UInt16()
        motor_msg.data = int(self.current_motor_pwm)
        self.motor_state_pub.publish(motor_msg)

        left_msg = UInt16()
        left_msg.data = int(self.current_left_pwm)
        self.left_pwm_pub.publish(left_msg)

        right_msg = UInt16()
        right_msg.data = int(self.current_right_pwm)
        self.right_pwm_pub.publish(right_msg)

        trim_msg = Int16MultiArray()
        trim_msg.data = [
            int(self.current_left_trim_pwm),
            int(self.current_right_trim_pwm),
        ]
        self.trim_state_pub.publish(trim_msg)

    def _height_percent_to_pwm(
        self,
        height_percent: float,
        left_trim_pwm: Optional[int] = None,
        right_trim_pwm: Optional[int] = None,
    ) -> tuple[int, int]:
        ratio = max(0.0, min(100.0, float(height_percent))) / 100.0
        resolved_left_trim_pwm = (
            self.current_left_trim_pwm if left_trim_pwm is None else int(left_trim_pwm)
        )
        resolved_right_trim_pwm = (
            self.current_right_trim_pwm if right_trim_pwm is None else int(right_trim_pwm)
        )
        left_pwm = round(
            self.height_servo_left_low_pwm +
            ratio * (self.height_servo_left_high_pwm - self.height_servo_left_low_pwm)
        ) + resolved_left_trim_pwm
        right_pwm = round(
            self.height_servo_right_low_pwm +
            ratio * (self.height_servo_right_high_pwm - self.height_servo_right_low_pwm)
        ) + resolved_right_trim_pwm
        return int(left_pwm), int(right_pwm)

    def _build_motor_command_sequence(self, target_pwm: int) -> tuple[List[ServoTarget], List[float]]:
        start_pwm = int(self.current_motor_pwm)
        commands: List[ServoTarget] = []
        delays_after_commands: List[float] = []

        if (
            start_pwm <= self.blade_motor_stop_pwm
            and target_pwm > self.blade_motor_stop_pwm
            and self.blade_motor_start_pop_duration_sec > 0.0
        ):
            pop_pwm = self.blade_motor_start_pop_pwm
            if pop_pwm != start_pwm:
                commands.append(ServoTarget(self.blade_motor_channel, pop_pwm))
                delays_after_commands.append(self.blade_motor_start_pop_duration_sec)
                start_pwm = pop_pwm

        if start_pwm == target_pwm and commands:
            return commands, delays_after_commands

        if start_pwm == target_pwm:
            return [ServoTarget(self.blade_motor_channel, target_pwm)], [0.0]

        direction = 1 if target_pwm > start_pwm else -1
        next_pwm = start_pwm

        while next_pwm != target_pwm:
            remaining = abs(target_pwm - next_pwm)
            delta = min(self.blade_motor_ramp_step_pwm, remaining)
            next_pwm += direction * delta
            commands.append(ServoTarget(self.blade_motor_channel, int(next_pwm)))
            delays_after_commands.append(self.blade_motor_ramp_interval_sec)

        return commands, delays_after_commands

    def _build_height_ramp_commands(
        self,
        target_height_percent: float,
    ) -> tuple[List[ServoTarget], List[float]]:
        target_left_pwm, target_right_pwm = self._height_percent_to_pwm(target_height_percent)
        return self._build_servo_pair_ramp_commands(target_left_pwm, target_right_pwm)

    def _build_servo_pair_ramp_commands(
        self,
        target_left_pwm: int,
        target_right_pwm: int,
    ) -> tuple[List[ServoTarget], List[float]]:
        current_left_pwm = int(self.current_left_pwm)
        current_right_pwm = int(self.current_right_pwm)

        if current_left_pwm == target_left_pwm and current_right_pwm == target_right_pwm:
            return (
                [
                    ServoTarget(self.height_servo_left_channel, target_left_pwm),
                    ServoTarget(self.height_servo_right_channel, target_right_pwm),
                ],
                [0.0, 0.0],
            )

        left_step_pwm = max(
            1,
            round(
                abs(self.height_servo_left_high_pwm - self.height_servo_left_low_pwm)
                * self.height_ramp_step_percent / 100.0
            ),
        )
        right_step_pwm = max(
            1,
            round(
                abs(self.height_servo_right_high_pwm - self.height_servo_right_low_pwm)
                * self.height_ramp_step_percent / 100.0
            ),
        )

        commands: List[ServoTarget] = []
        delays_after_commands: List[float] = []

        while current_left_pwm != target_left_pwm or current_right_pwm != target_right_pwm:
            current_left_pwm = self._step_towards_pwm(
                current_left_pwm,
                target_left_pwm,
                left_step_pwm,
            )
            current_right_pwm = self._step_towards_pwm(
                current_right_pwm,
                target_right_pwm,
                right_step_pwm,
            )
            commands.append(ServoTarget(self.height_servo_left_channel, current_left_pwm))
            delays_after_commands.append(0.0)
            commands.append(ServoTarget(self.height_servo_right_channel, current_right_pwm))
            delays_after_commands.append(self.height_ramp_interval_sec)

        return commands, delays_after_commands

    def _make_motor_command_group(self, pwm: int, label: Optional[str] = None) -> CommandGroup:
        resolved_label = label
        if resolved_label is None:
            resolved_label = f'blade motor target {pwm}'

        return CommandGroup(
            label=resolved_label,
            commands=[],
            motor_pwm=pwm,
        )

    def _step_towards_pwm(self, current_pwm: int, target_pwm: int, step_pwm: int) -> int:
        if current_pwm == target_pwm:
            return current_pwm

        direction = 1 if target_pwm > current_pwm else -1
        delta = min(step_pwm, abs(target_pwm - current_pwm))
        return int(current_pwm + direction * delta)

    def _is_height_spin_locked(self) -> bool:
        if self.current_height_percent >= self.blade_height_spin_lock_percent:
            return True

        if (
            self.active_group is not None
            and self.active_group.height_percent is not None
            and self.active_group.height_percent >= self.blade_height_spin_lock_percent
        ):
            return True

        return any(
            group.height_percent is not None
            and group.height_percent >= self.blade_height_spin_lock_percent
            for group in self.pending_groups
        )

    def _normalize_motor_target_pwm(self, value: int) -> int:
        requested = int(value)

        if requested <= self.blade_motor_stop_pwm:
            normalized = max(self.blade_motor_min_pwm, self.blade_motor_stop_pwm)
            if requested != normalized:
                self.get_logger().warn(
                    f'blade motor pwm {requested} below stop threshold; clamped to {normalized}'
                )
            return normalized

        if requested < self.blade_motor_min_running_pwm:
            self.get_logger().warn(
                f'blade motor pwm {requested} below minimum running speed; '
                f'clamped to {self.blade_motor_min_running_pwm}'
            )
            return self.blade_motor_min_running_pwm

        if requested > self.blade_motor_max_pwm:
            self.get_logger().warn(
                f'blade motor pwm {requested} above maximum; clamped to {self.blade_motor_max_pwm}'
            )
            return self.blade_motor_max_pwm

        return requested

    def _clamp_float(self, value: float, minimum: float, maximum: float, label: str) -> float:
        clamped = max(minimum, min(maximum, float(value)))
        if clamped != value:
            self.get_logger().warn(
                f'{label} {value} out of range; clamped to {clamped}'
            )
        return clamped

    def _clamp_int(self, value: int, minimum: int, maximum: int, label: str) -> int:
        clamped = max(minimum, min(maximum, int(value)))
        if clamped != value:
            self.get_logger().warn(
                f'{label} {value} out of range; clamped to {clamped}'
            )
        return clamped


def main(args=None) -> None:
    rclpy.init(args=args)
    node = BladeController()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
