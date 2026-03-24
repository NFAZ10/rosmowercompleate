#!/usr/bin/env python3
"""
MQTT bridge for ROS Mower.

This node forwards a curated set of ROS 2 telemetry topics to MQTT and accepts
MQTT control commands for the most useful robot actions.
"""

import json
import math
from datetime import datetime, timezone
from typing import Any, Dict

import paho.mqtt.client as mqtt
import rclpy
from geometry_msgs.msg import PoseStamped, Twist, TwistStamped
from nav_msgs.msg import Odometry
from rcl_interfaces.msg import ParameterDescriptor
from rclpy.node import Node
from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy
from sensor_msgs.msg import BatteryState, Imu, NavSatFix
from std_msgs.msg import Bool, Float32, String


class MQTTBridgeNode(Node):
    def __init__(self):
        super().__init__('mqtt_bridge_node')

        string_parameter = ParameterDescriptor(dynamic_typing=True)

        self.declare_parameter('mqtt_broker', 'homeassistant.local', string_parameter)
        self.declare_parameter('mqtt_port', 1883)
        self.declare_parameter('mqtt_username', '', string_parameter)
        self.declare_parameter('mqtt_password', '', string_parameter)
        self.declare_parameter('mqtt_client_id', 'rosmower_mqtt_bridge', string_parameter)
        self.declare_parameter('mqtt_keepalive', 60)
        self.declare_parameter('mqtt_qos', 1)
        self.declare_parameter('base_topic', 'rosmower', string_parameter)
        self.declare_parameter('retain_telemetry', True)
        self.declare_parameter('status_interval_sec', 5.0)
        self.declare_parameter('snapshot_interval_sec', 2.0)

        self.broker = str(self.get_parameter('mqtt_broker').value)
        self.port = int(self.get_parameter('mqtt_port').value)
        self.username = str(self.get_parameter('mqtt_username').value)
        self.password = str(self.get_parameter('mqtt_password').value)
        self.client_id = str(self.get_parameter('mqtt_client_id').value)
        self.keepalive = int(self.get_parameter('mqtt_keepalive').value)
        self.mqtt_qos = max(0, min(int(self.get_parameter('mqtt_qos').value), 2))
        self.base_topic = str(self.get_parameter('base_topic').value).strip('/')
        self.retain_telemetry = bool(self.get_parameter('retain_telemetry').value)
        self.status_interval = float(self.get_parameter('status_interval_sec').value)
        self.snapshot_interval = float(self.get_parameter('snapshot_interval_sec').value)

        self.availability_topic = self._mqtt_topic('bridge/availability')
        self.status_topic = self._mqtt_topic('bridge/status')
        self.snapshot_topic = self._mqtt_topic('state')
        self.mqtt_connected = False
        self.latest_state: Dict[str, Any] = {}
        self.state_dirty = False

        sensor_qos = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10,
        )
        default_qos = 10

        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.robot_mode_cmd_pub = self.create_publisher(String, '/robot_mode_cmd', 10)
        self.mission_command_pub = self.create_publisher(String, '/mission/command', 10)
        self.dock_command_pub = self.create_publisher(String, '/dock/command', 10)
        self.goal_pose_pub = self.create_publisher(PoseStamped, '/goal_pose', 10)

        self.command_handlers = {
            self._mqtt_topic('cmd_vel'): self._handle_cmd_vel_command,
            self._mqtt_topic('command'): self._handle_generic_command,
            self._mqtt_topic('command/cmd_vel'): self._handle_cmd_vel_command,
            self._mqtt_topic('command/robot_mode'): self._handle_robot_mode_command,
            self._mqtt_topic('command/mission'): self._handle_mission_command,
            self._mqtt_topic('command/dock'): self._handle_dock_command,
            self._mqtt_topic('command/goal_pose'): self._handle_goal_pose_command,
        }

        self.ros_to_mqtt_mappings = [
            {
                'ros_topic': '/gps/fix',
                'msg_type': NavSatFix,
                'mqtt_suffix': 'gps/fix',
                'state_key': 'gps_fix',
                'converter': self.navsat_to_dict,
                'qos': sensor_qos,
            },
            {
                'ros_topic': '/gps/velocity',
                'msg_type': TwistStamped,
                'mqtt_suffix': 'gps/velocity',
                'state_key': 'gps_velocity',
                'converter': self.twist_stamped_to_dict,
                'qos': sensor_qos,
            },
            {
                'ros_topic': '/imu/data',
                'msg_type': Imu,
                'mqtt_suffix': 'imu/data',
                'state_key': 'imu_data',
                'converter': self.imu_to_dict,
                'qos': sensor_qos,
            },
            {
                'ros_topic': '/odom',
                'msg_type': Odometry,
                'mqtt_suffix': 'odom',
                'state_key': 'odom',
                'converter': self.odom_to_dict,
                'qos': sensor_qos,
            },
            {
                'ros_topic': '/cmd_vel',
                'msg_type': Twist,
                'mqtt_suffix': 'cmd_vel',
                'state_key': 'cmd_vel',
                'converter': self.twist_to_dict,
                'qos': default_qos,
            },
            {
                'ros_topic': '/pose',
                'msg_type': PoseStamped,
                'mqtt_suffix': 'pose',
                'state_key': 'pose',
                'converter': self.pose_to_dict,
                'qos': default_qos,
            },
            {
                'ros_topic': '/goal_pose',
                'msg_type': PoseStamped,
                'mqtt_suffix': 'goal_pose',
                'state_key': 'goal_pose',
                'converter': self.pose_to_dict,
                'qos': default_qos,
            },
            {
                'ros_topic': '/mavros/battery',
                'msg_type': BatteryState,
                'mqtt_suffix': 'battery',
                'state_key': 'battery',
                'converter': self.battery_to_dict,
                'qos': sensor_qos,
            },
            {
                'ros_topic': '/voltage',
                'msg_type': Float32,
                'mqtt_suffix': 'battery/voltage',
                'state_key': 'battery_voltage',
                'converter': lambda msg: {'voltage': float(msg.data)},
                'qos': default_qos,
            },
            {
                'ros_topic': '/percent',
                'msg_type': Float32,
                'mqtt_suffix': 'battery/percent',
                'state_key': 'battery_percent',
                'converter': lambda msg: {'percent': float(msg.data)},
                'qos': default_qos,
            },
            {
                'ros_topic': '/current',
                'msg_type': Float32,
                'mqtt_suffix': 'battery/current',
                'state_key': 'battery_current',
                'converter': lambda msg: {'current': float(msg.data)},
                'qos': default_qos,
            },
            {
                'ros_topic': '/battery/state',
                'msg_type': String,
                'mqtt_suffix': 'battery/state',
                'state_key': 'battery_state',
                'converter': lambda msg: {'state': msg.data},
                'qos': default_qos,
            },
            {
                'ros_topic': '/battery/low',
                'msg_type': Bool,
                'mqtt_suffix': 'battery/low',
                'state_key': 'battery_low',
                'converter': lambda msg: {'low': bool(msg.data)},
                'qos': default_qos,
            },
            {
                'ros_topic': '/robot_mode',
                'msg_type': String,
                'mqtt_suffix': 'robot_mode',
                'mqtt_aliases': ['mode'],
                'state_key': 'robot_mode',
                'converter': lambda msg: {'mode': msg.data},
                'qos': default_qos,
            },
            {
                'ros_topic': '/robot_mode_cmd',
                'msg_type': String,
                'mqtt_suffix': 'robot_mode_cmd',
                'state_key': 'robot_mode_command',
                'converter': lambda msg: {'mode': msg.data},
                'qos': default_qos,
            },
            {
                'ros_topic': '/mission/state',
                'msg_type': String,
                'mqtt_suffix': 'mission/state',
                'state_key': 'mission_state',
                'converter': lambda msg: {'state': msg.data},
                'qos': default_qos,
            },
            {
                'ros_topic': '/mission/active_zone',
                'msg_type': String,
                'mqtt_suffix': 'mission/active_zone',
                'state_key': 'mission_active_zone',
                'converter': lambda msg: {'zone_id': msg.data},
                'qos': default_qos,
            },
            {
                'ros_topic': '/mission/progress',
                'msg_type': String,
                'mqtt_suffix': 'mission/progress',
                'state_key': 'mission_progress',
                'converter': lambda msg: self.json_string_to_payload(msg.data, fallback_key='progress'),
                'qos': default_qos,
            },
            {
                'ros_topic': '/mission/command',
                'msg_type': String,
                'mqtt_suffix': 'mission/command',
                'state_key': 'mission_command',
                'converter': lambda msg: {'command': msg.data},
                'qos': default_qos,
            },
            {
                'ros_topic': '/dock/status',
                'msg_type': String,
                'mqtt_suffix': 'dock/status',
                'state_key': 'dock_status',
                'converter': lambda msg: {'status': msg.data},
                'qos': default_qos,
            },
            {
                'ros_topic': '/dock/pose',
                'msg_type': PoseStamped,
                'mqtt_suffix': 'dock/pose',
                'state_key': 'dock_pose',
                'converter': self.pose_to_dict,
                'qos': default_qos,
            },
            {
                'ros_topic': '/dock/gps',
                'msg_type': NavSatFix,
                'mqtt_suffix': 'dock/gps',
                'state_key': 'dock_gps',
                'converter': self.navsat_to_dict,
                'qos': default_qos,
            },
            {
                'ros_topic': '/enable_motors',
                'msg_type': Bool,
                'mqtt_suffix': 'enable/motors',
                'state_key': 'enable_motors',
                'converter': lambda msg: {'enabled': bool(msg.data)},
                'qos': default_qos,
            },
            {
                'ros_topic': '/enable_sensors',
                'msg_type': Bool,
                'mqtt_suffix': 'enable/sensors',
                'state_key': 'enable_sensors',
                'converter': lambda msg: {'enabled': bool(msg.data)},
                'qos': default_qos,
            },
            {
                'ros_topic': '/enable_gps',
                'msg_type': Bool,
                'mqtt_suffix': 'enable/gps',
                'state_key': 'enable_gps',
                'converter': lambda msg: {'enabled': bool(msg.data)},
                'qos': default_qos,
            },
            {
                'ros_topic': '/enable_lidar',
                'msg_type': Bool,
                'mqtt_suffix': 'enable/lidar',
                'state_key': 'enable_lidar',
                'converter': lambda msg: {'enabled': bool(msg.data)},
                'qos': default_qos,
            },
            {
                'ros_topic': '/enable_camera',
                'msg_type': Bool,
                'mqtt_suffix': 'enable/camera',
                'state_key': 'enable_camera',
                'converter': lambda msg: {'enabled': bool(msg.data)},
                'qos': default_qos,
            },
        ]

        for mapping in self.ros_to_mqtt_mappings:
            self.create_subscription(
                mapping['msg_type'],
                mapping['ros_topic'],
                lambda msg, mapping=mapping: self._forward_ros_message(mapping, msg),
                mapping['qos'],
            )

        self.mqtt_client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv311)
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.reconnect_delay_set(min_delay=1, max_delay=30)
        self.mqtt_client.will_set(
            self.availability_topic,
            payload='offline',
            qos=self.mqtt_qos,
            retain=True,
        )

        if self.username:
            self.mqtt_client.username_pw_set(self.username, self.password or None)

        try:
            self.get_logger().info(
                'Starting MQTT bridge '
                f'(broker={self.broker}:{self.port}, base_topic={self.base_topic}, '
                f'username_set={bool(self.username)})'
            )
            self.mqtt_client.connect_async(self.broker, self.port, self.keepalive)
            self.mqtt_client.loop_start()
        except Exception as exc:
            self.get_logger().error(f'Failed to start MQTT client: {exc}')

        self.create_timer(self.status_interval, self.publish_status)
        self.create_timer(self.snapshot_interval, self.publish_snapshot)

        self.get_logger().info(
            f'Configured {len(self.ros_to_mqtt_mappings)} ROS topics and '
            f'{len(self.command_handlers)} MQTT command topics'
        )

    def _mqtt_topic(self, suffix: str) -> str:
        suffix = suffix.strip('/')
        return f'{self.base_topic}/{suffix}' if self.base_topic else suffix

    def _forward_ros_message(self, mapping: Dict[str, Any], msg: Any) -> None:
        try:
            payload = mapping['converter'](msg)
        except Exception as exc:
            self.get_logger().error(
                f'Failed to convert ROS topic {mapping["ros_topic"]} for MQTT: {exc}'
            )
            return

        self._cache_state(mapping['state_key'], payload)
        mqtt_suffixes = [mapping['mqtt_suffix'], *mapping.get('mqtt_aliases', [])]
        for mqtt_suffix in mqtt_suffixes:
            mqtt_topic = self._mqtt_topic(mqtt_suffix)
            self.publish_to_mqtt(mqtt_topic, payload)

    def _cache_state(self, key: str, payload: Any) -> None:
        self.latest_state[key] = payload
        self.latest_state['last_update'] = {'timestamp': self._now_iso()}
        self.state_dirty = True

    def on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        if rc != 0:
            self.mqtt_connected = False
            self.get_logger().error(f'Failed to connect to MQTT broker: rc={rc}')
            return

        self.mqtt_connected = True
        self.get_logger().info('Connected to MQTT broker')
        self.publish_text_to_mqtt(self.availability_topic, 'online', retain=True)

        for topic in sorted(self.command_handlers):
            client.subscribe(topic, qos=self.mqtt_qos)
            self.get_logger().info(f'Subscribed to MQTT command topic: {topic}')

        self.publish_status()
        self.publish_snapshot(force=True)

    def on_mqtt_disconnect(self, client, userdata, rc, properties=None):
        was_connected = self.mqtt_connected
        self.mqtt_connected = False
        if rc == 0:
            if was_connected:
                self.get_logger().info('Disconnected from MQTT broker')
        else:
            self.get_logger().warning(f'Unexpected MQTT disconnect: rc={rc}')

    def on_mqtt_message(self, client, userdata, msg):
        handler = self.command_handlers.get(msg.topic)
        if handler is None:
            self.get_logger().warning(f'No handler registered for MQTT topic: {msg.topic}')
            return

        payload_text = msg.payload.decode().strip()
        self.get_logger().info(f'Received MQTT command on {msg.topic}: {payload_text}')
        try:
            handler(payload_text)
        except ValueError as exc:
            self.get_logger().error(f'Invalid MQTT payload on {msg.topic}: {exc}')
        except Exception as exc:
            self.get_logger().error(f'Error processing MQTT message on {msg.topic}: {exc}')

    def _handle_cmd_vel_command(self, payload_text: str) -> None:
        payload = self.require_object_payload(payload_text, 'cmd_vel')
        twist = Twist()
        linear = payload.get('linear', {})
        angular = payload.get('angular', {})

        twist.linear.x = float(linear.get('x', payload.get('linear_x', 0.0)))
        twist.linear.y = float(linear.get('y', payload.get('linear_y', 0.0)))
        twist.linear.z = float(linear.get('z', payload.get('linear_z', 0.0)))
        twist.angular.x = float(angular.get('x', payload.get('angular_x', 0.0)))
        twist.angular.y = float(angular.get('y', payload.get('angular_y', 0.0)))
        twist.angular.z = float(angular.get('z', payload.get('angular_z', payload.get('yaw_rate', 0.0))))

        self.cmd_vel_pub.publish(twist)

    def _handle_robot_mode_command(self, payload_text: str) -> None:
        mode = self.extract_string_payload(payload_text, 'robot mode', 'mode', 'value', 'data', 'command')
        msg = String()
        msg.data = mode.lower()
        self.robot_mode_cmd_pub.publish(msg)

    def _handle_mission_command(self, payload_text: str) -> None:
        command = self.extract_string_payload(
            payload_text,
            'mission command',
            'command',
            'value',
            'data',
            'mission_command',
        )
        msg = String()
        msg.data = command.upper()
        self.mission_command_pub.publish(msg)

    def _handle_dock_command(self, payload_text: str) -> None:
        command = self.extract_string_payload(
            payload_text,
            'dock command',
            'command',
            'value',
            'data',
            'dock_command',
        )
        msg = String()
        msg.data = command.upper()
        self.dock_command_pub.publish(msg)

    def _handle_goal_pose_command(self, payload_text: str) -> None:
        payload = self.require_object_payload(payload_text, 'goal_pose')
        pose = PoseStamped()
        pose.header.frame_id = (
            payload.get('frame_id')
            or payload.get('header', {}).get('frame_id')
            or 'map'
        )
        pose.header.stamp = self.get_clock().now().to_msg()

        position = payload.get('position', payload)
        pose.pose.position.x = float(position.get('x', 0.0))
        pose.pose.position.y = float(position.get('y', 0.0))
        pose.pose.position.z = float(position.get('z', 0.0))

        orientation = payload.get('orientation', {})
        if any(key in orientation for key in ('x', 'y', 'z', 'w')):
            pose.pose.orientation.x = float(orientation.get('x', 0.0))
            pose.pose.orientation.y = float(orientation.get('y', 0.0))
            pose.pose.orientation.z = float(orientation.get('z', 0.0))
            pose.pose.orientation.w = float(orientation.get('w', 1.0))
        else:
            yaw = float(payload.get('yaw', 0.0))
            pose.pose.orientation.z = math.sin(yaw / 2.0)
            pose.pose.orientation.w = math.cos(yaw / 2.0)

        self.goal_pose_pub.publish(pose)

    def _handle_generic_command(self, payload_text: str) -> None:
        payload = self.require_object_payload(payload_text, 'generic command')
        target = str(
            payload.get('target')
            or payload.get('type')
            or payload.get('command_topic')
            or payload.get('topic')
            or ''
        ).strip().lower()
        nested_payload = payload.get('payload', payload)

        if target in ('cmd_vel', 'twist'):
            self._handle_cmd_vel_command(json.dumps(nested_payload))
        elif target in ('robot_mode', 'robot_mode_cmd', 'mode'):
            self._handle_robot_mode_command(json.dumps(nested_payload))
        elif target in ('mission', 'mission_command', 'mission/command'):
            self._handle_mission_command(json.dumps(nested_payload))
        elif target in ('dock', 'dock_command', 'dock/command'):
            self._handle_dock_command(json.dumps(nested_payload))
        elif target in ('goal_pose', 'goal'):
            self._handle_goal_pose_command(json.dumps(nested_payload))
        else:
            raise ValueError(
                'generic command payload must contain a target of '
                'cmd_vel, robot_mode, mission, dock, or goal_pose'
            )

    def decode_payload(self, payload_text: str) -> Any:
        if not payload_text:
            raise ValueError('payload is empty')
        try:
            return json.loads(payload_text)
        except json.JSONDecodeError:
            return payload_text

    def require_object_payload(self, payload_text: str, payload_name: str) -> Dict[str, Any]:
        payload = self.decode_payload(payload_text)
        if not isinstance(payload, dict):
            raise ValueError(f'{payload_name} payload must be a JSON object')
        return payload

    def extract_string_payload(
        self,
        payload_text: str,
        payload_name: str,
        *field_names: str,
    ) -> str:
        payload = self.decode_payload(payload_text)
        if isinstance(payload, str):
            value = payload
        elif isinstance(payload, dict):
            value = None
            for field_name in field_names:
                candidate = payload.get(field_name)
                if candidate is not None:
                    value = candidate
                    break
            if value is None:
                raise ValueError(
                    f'{payload_name} payload must include one of: {", ".join(field_names)}'
                )
        else:
            raise ValueError(f'{payload_name} payload must be a string or JSON object')

        text = str(value).strip()
        if not text:
            raise ValueError(f'{payload_name} payload cannot be empty')
        return text

    def publish_text_to_mqtt(self, topic: str, text: str, retain: bool = True) -> bool:
        if not self.mqtt_connected:
            return False
        result = self.mqtt_client.publish(topic, text, qos=self.mqtt_qos, retain=retain)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            self.get_logger().error(f'Failed to publish MQTT text to {topic}: rc={result.rc}')
            return False
        return True

    def publish_to_mqtt(self, topic: str, data: Any, retain: bool = None) -> bool:
        if retain is None:
            retain = self.retain_telemetry
        if not self.mqtt_connected:
            return False

        try:
            payload = json.dumps(data, ensure_ascii=True, separators=(',', ':'))
        except TypeError as exc:
            self.get_logger().error(f'Failed to serialize MQTT payload for {topic}: {exc}')
            return False

        result = self.mqtt_client.publish(topic, payload, qos=self.mqtt_qos, retain=retain)
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            self.get_logger().error(f'Failed to publish MQTT message to {topic}: rc={result.rc}')
            return False
        return True

    def publish_status(self) -> None:
        status = {
            'timestamp': self._now_iso(),
            'node': self.get_name(),
            'mqtt_connected': self.mqtt_connected,
            'broker': self.broker,
            'port': self.port,
            'base_topic': self.base_topic,
            'telemetry_topic_count': len(self.ros_to_mqtt_mappings),
            'command_topic_count': len(self.command_handlers),
        }
        self._cache_state('bridge_status', status)
        self.publish_to_mqtt(self.status_topic, status, retain=True)

    def publish_snapshot(self, force: bool = False) -> None:
        if not force and not self.state_dirty:
            return

        snapshot = dict(self.latest_state)
        snapshot['timestamp'] = self._now_iso()
        snapshot['bridge'] = {
            'mqtt_connected': self.mqtt_connected,
            'broker': self.broker,
            'port': self.port,
            'base_topic': self.base_topic,
        }

        if self.publish_to_mqtt(self.snapshot_topic, snapshot, retain=True):
            self.state_dirty = False

    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def header_to_dict(self, header) -> Dict[str, Any]:
        return {
            'stamp': {
                'sec': header.stamp.sec,
                'nanosec': header.stamp.nanosec,
            },
            'frame_id': header.frame_id,
        }

    def point_to_dict(self, point) -> Dict[str, float]:
        return {
            'x': float(point.x),
            'y': float(point.y),
            'z': float(point.z),
        }

    def quaternion_to_dict(self, quaternion) -> Dict[str, float]:
        return {
            'x': float(quaternion.x),
            'y': float(quaternion.y),
            'z': float(quaternion.z),
            'w': float(quaternion.w),
        }

    def vector3_to_dict(self, vector) -> Dict[str, float]:
        return {
            'x': float(vector.x),
            'y': float(vector.y),
            'z': float(vector.z),
        }

    def navsat_to_dict(self, msg: NavSatFix) -> Dict[str, Any]:
        return {
            'header': self.header_to_dict(msg.header),
            'latitude': float(msg.latitude),
            'longitude': float(msg.longitude),
            'altitude': float(msg.altitude),
            'status': int(msg.status.status),
            'service': int(msg.status.service),
            'position_covariance': list(msg.position_covariance),
            'position_covariance_type': int(msg.position_covariance_type),
        }

    def imu_to_dict(self, msg: Imu) -> Dict[str, Any]:
        return {
            'header': self.header_to_dict(msg.header),
            'orientation': self.quaternion_to_dict(msg.orientation),
            'orientation_covariance': list(msg.orientation_covariance),
            'angular_velocity': self.vector3_to_dict(msg.angular_velocity),
            'angular_velocity_covariance': list(msg.angular_velocity_covariance),
            'linear_acceleration': self.vector3_to_dict(msg.linear_acceleration),
            'linear_acceleration_covariance': list(msg.linear_acceleration_covariance),
        }

    def twist_to_dict(self, msg: Twist) -> Dict[str, Any]:
        return {
            'linear': self.vector3_to_dict(msg.linear),
            'angular': self.vector3_to_dict(msg.angular),
        }

    def twist_stamped_to_dict(self, msg: TwistStamped) -> Dict[str, Any]:
        return {
            'header': self.header_to_dict(msg.header),
            'twist': self.twist_to_dict(msg.twist),
        }

    def odom_to_dict(self, msg: Odometry) -> Dict[str, Any]:
        return {
            'header': self.header_to_dict(msg.header),
            'child_frame_id': msg.child_frame_id,
            'pose': {
                'position': self.point_to_dict(msg.pose.pose.position),
                'orientation': self.quaternion_to_dict(msg.pose.pose.orientation),
                'covariance': list(msg.pose.covariance),
            },
            'twist': {
                'linear': self.vector3_to_dict(msg.twist.twist.linear),
                'angular': self.vector3_to_dict(msg.twist.twist.angular),
                'covariance': list(msg.twist.covariance),
            },
        }

    def pose_to_dict(self, msg: PoseStamped) -> Dict[str, Any]:
        return {
            'header': self.header_to_dict(msg.header),
            'position': self.point_to_dict(msg.pose.position),
            'orientation': self.quaternion_to_dict(msg.pose.orientation),
        }

    def battery_to_dict(self, msg: BatteryState) -> Dict[str, Any]:
        percentage = None
        if msg.percentage >= 0.0:
            percentage = (
                float(msg.percentage * 100.0)
                if msg.percentage <= 1.0
                else float(msg.percentage)
            )

        return {
            'header': self.header_to_dict(msg.header),
            'voltage': float(msg.voltage),
            'current': float(msg.current),
            'charge': float(msg.charge),
            'capacity': float(msg.capacity),
            'design_capacity': float(msg.design_capacity),
            'percentage': percentage,
            'power_supply_status': int(msg.power_supply_status),
            'power_supply_health': int(msg.power_supply_health),
            'power_supply_technology': int(msg.power_supply_technology),
            'present': bool(msg.present),
            'location': msg.location,
            'serial_number': msg.serial_number,
        }

    def json_string_to_payload(self, raw: str, fallback_key: str = 'value') -> Dict[str, Any]:
        text = raw.strip()
        if not text:
            return {fallback_key: ''}
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return {fallback_key: text}

        if isinstance(parsed, dict):
            return parsed
        return {fallback_key: parsed}

    def destroy_node(self):
        try:
            if hasattr(self, 'mqtt_client'):
                if self.mqtt_connected:
                    self.publish_text_to_mqtt(self.availability_topic, 'offline', retain=True)
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
        finally:
            super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = MQTTBridgeNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
