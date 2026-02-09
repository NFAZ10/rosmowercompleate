#!/usr/bin/env python3
"""
MQTT Bridge Node for ROS Mower
Bridges ROS2 topics to/from MQTT broker
"""

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
import paho.mqtt.client as mqtt
import json
from std_msgs.msg import String, Float32
from sensor_msgs.msg import NavSatFix, Imu, Image, CompressedImage, BatteryState
from geometry_msgs.msg import Twist, PoseStamped
from nav_msgs.msg import Odometry
import base64


class MQTTBridgeNode(Node):
    def __init__(self):
        super().__init__('mqtt_bridge_node')
        
        # Declare parameters
        self.declare_parameter('mqtt_broker', 'localhost')
        self.declare_parameter('mqtt_port', 1883)
        self.declare_parameter('mqtt_username', '')
        self.declare_parameter('mqtt_password', '')
        self.declare_parameter('mqtt_client_id', 'rosmower_mqtt_bridge')
        self.declare_parameter('mqtt_keepalive', 60)
        self.declare_parameter('base_topic', 'rosmower')
        
        # Get parameters
        self.broker = self.get_parameter('mqtt_broker').value
        self.port = self.get_parameter('mqtt_port').value
        self.username = self.get_parameter('mqtt_username').value
        self.password = self.get_parameter('mqtt_password').value
        self.client_id = self.get_parameter('mqtt_client_id').value
        self.keepalive = self.get_parameter('mqtt_keepalive').value
        self.base_topic = self.get_parameter('base_topic').value
        
        # QoS profile
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )
        
        # ROS Subscribers - publish to MQTT
        self.create_subscription(
            NavSatFix,
            '/gps/fix',
            lambda msg: self.publish_to_mqtt(f'{self.base_topic}/gps/fix', self.navsat_to_dict(msg)),
            qos_profile
        )
        
        self.create_subscription(
            Imu,
            '/imu/data',
            lambda msg: self.publish_to_mqtt(f'{self.base_topic}/imu/data', self.imu_to_dict(msg)),
            qos_profile
        )
        
        self.create_subscription(
            Odometry,
            '/odom',
            lambda msg: self.publish_to_mqtt(f'{self.base_topic}/odom', self.odom_to_dict(msg)),
            qos_profile
        )
        
        self.create_subscription(
            PoseStamped,
            '/pose',
            lambda msg: self.publish_to_mqtt(f'{self.base_topic}/pose', self.pose_to_dict(msg)),
            qos_profile
        )
        
        # Battery data subscriptions
        self.create_subscription(
            BatteryState,
            '/mavros/battery',
            lambda msg: self.publish_to_mqtt(f'{self.base_topic}/battery', self.battery_to_dict(msg)),
            qos_profile
        )
        
        self.create_subscription(
            Float32,
            '/voltage',
            lambda msg: self.publish_to_mqtt(f'{self.base_topic}/battery/voltage', {'voltage': msg.data}),
            qos_profile
        )
        
        self.create_subscription(
            Float32,
            '/percent',
            lambda msg: self.publish_to_mqtt(f'{self.base_topic}/battery/percent', {'percent': msg.data}),
            qos_profile
        )
        
        # Mode status subscription
        self.create_subscription(
            String,
            '/robot_mode',
            lambda msg: self.publish_to_mqtt(f'{self.base_topic}/mode', {'mode': msg.data}),
            10
        )
        
        # Status publisher
        self.status_timer = self.create_timer(5.0, self.publish_status)
        
        # ROS Publishers - subscribe from MQTT
        self.cmd_vel_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        
        # Setup MQTT client
        self.mqtt_client = mqtt.Client(client_id=self.client_id)
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        
        if self.username and self.password:
            self.mqtt_client.username_pw_set(self.username, self.password)
        
        # Connect to MQTT broker
        try:
            self.get_logger().info(f'Connecting to MQTT broker at {self.broker}:{self.port}')
            self.mqtt_client.connect(self.broker, self.port, self.keepalive)
            self.mqtt_client.loop_start()
        except Exception as e:
            self.get_logger().error(f'Failed to connect to MQTT broker: {e}')
    
    def on_mqtt_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            self.get_logger().info('Connected to MQTT broker')
            # Subscribe to command topics
            self.mqtt_client.subscribe(f'{self.base_topic}/cmd_vel')
            self.mqtt_client.subscribe(f'{self.base_topic}/command')
        else:
            self.get_logger().error(f'Failed to connect to MQTT broker: {rc}')
    
    def on_mqtt_disconnect(self, client, userdata, rc):
        """Callback when disconnected from MQTT broker"""
        self.get_logger().warning(f'Disconnected from MQTT broker: {rc}')
    
    def on_mqtt_message(self, client, userdata, msg):
        """Callback when MQTT message received"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            if topic == f'{self.base_topic}/cmd_vel':
                # Convert to Twist message
                twist = Twist()
                twist.linear.x = payload.get('linear', {}).get('x', 0.0)
                twist.linear.y = payload.get('linear', {}).get('y', 0.0)
                twist.linear.z = payload.get('linear', {}).get('z', 0.0)
                twist.angular.x = payload.get('angular', {}).get('x', 0.0)
                twist.angular.y = payload.get('angular', {}).get('y', 0.0)
                twist.angular.z = payload.get('angular', {}).get('z', 0.0)
                self.cmd_vel_pub.publish(twist)
                self.get_logger().debug(f'Published cmd_vel: {twist}')
            
            elif topic == f'{self.base_topic}/command':
                self.get_logger().info(f'Received command: {payload}')
                # Handle custom commands here
                
        except Exception as e:
            self.get_logger().error(f'Error processing MQTT message: {e}')
    
    def publish_to_mqtt(self, topic, data):
        """Publish data to MQTT"""
        try:
            payload = json.dumps(data)
            self.mqtt_client.publish(topic, payload)
            self.get_logger().debug(f'Published to {topic}')
        except Exception as e:
            self.get_logger().error(f'Error publishing to MQTT: {e}')
    
    def publish_status(self):
        """Publish system status"""
        status = {
            'timestamp': self.get_clock().now().to_msg().sec,
            'node': self.get_name(),
            'mqtt_connected': self.mqtt_client.is_connected(),
            'broker': self.broker
        }
        self.publish_to_mqtt(f'{self.base_topic}/status', status)
    
    def navsat_to_dict(self, msg):
        """Convert NavSatFix to dictionary"""
        return {
            'latitude': msg.latitude,
            'longitude': msg.longitude,
            'altitude': msg.altitude,
            'status': msg.status.status,
            'service': msg.status.service
        }
    
    def imu_to_dict(self, msg):
        """Convert IMU to dictionary"""
        return {
            'orientation': {
                'x': msg.orientation.x,
                'y': msg.orientation.y,
                'z': msg.orientation.z,
                'w': msg.orientation.w
            },
            'angular_velocity': {
                'x': msg.angular_velocity.x,
                'y': msg.angular_velocity.y,
                'z': msg.angular_velocity.z
            },
            'linear_acceleration': {
                'x': msg.linear_acceleration.x,
                'y': msg.linear_acceleration.y,
                'z': msg.linear_acceleration.z
            }
        }
    
    def odom_to_dict(self, msg):
        """Convert Odometry to dictionary"""
        return {
            'position': {
                'x': msg.pose.pose.position.x,
                'y': msg.pose.pose.position.y,
                'z': msg.pose.pose.position.z
            },
            'orientation': {
                'x': msg.pose.pose.orientation.x,
                'y': msg.pose.pose.orientation.y,
                'z': msg.pose.pose.orientation.z,
                'w': msg.pose.pose.orientation.w
            },
            'linear_velocity': {
                'x': msg.twist.twist.linear.x,
                'y': msg.twist.twist.linear.y,
                'z': msg.twist.twist.linear.z
            },
            'angular_velocity': {
                'x': msg.twist.twist.angular.x,
                'y': msg.twist.twist.angular.y,
                'z': msg.twist.twist.angular.z
            }
        }
    
    def pose_to_dict(self, msg):
        """Convert PoseStamped to dictionary"""
        return {
            'position': {
                'x': msg.pose.position.x,
                'y': msg.pose.position.y,
                'z': msg.pose.position.z
            },
            'orientation': {
                'x': msg.pose.orientation.x,
                'y': msg.pose.orientation.y,
                'z': msg.pose.orientation.z,
                'w': msg.pose.orientation.w
            }
        }
    
    def battery_to_dict(self, msg):
        """Convert BatteryState to dictionary"""
        return {
            'voltage': msg.voltage,
            'current': msg.current,
            'charge': msg.charge,
            'capacity': msg.capacity,
            'design_capacity': msg.design_capacity,
            'percentage': msg.percentage * 100.0 if msg.percentage <= 1.0 else msg.percentage,  # Convert to 0-100
            'power_supply_status': msg.power_supply_status,
            'power_supply_health': msg.power_supply_health,
            'power_supply_technology': msg.power_supply_technology,
            'present': msg.present,
            'location': msg.location,
            'serial_number': msg.serial_number
        }
    
    def destroy_node(self):
        """Cleanup when node is destroyed"""
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
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
