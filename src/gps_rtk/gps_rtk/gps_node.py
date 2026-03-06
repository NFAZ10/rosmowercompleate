#!/usr/bin/env python3

"""
GPS/RTK ROS2 Node for receiving GPS data via UART on 40-pin header.
Supports NMEA protocol (standard GPS output format) with NTRIP RTK corrections.
Lifecycle managed node with enable/disable control.
"""

import rclpy
from rclpy.lifecycle import Node, State, TransitionCallbackReturn
from rclpy.lifecycle import Publisher
from sensor_msgs.msg import NavSatFix, NavSatStatus
from geometry_msgs.msg import TwistStamped
from std_msgs.msg import String, Bool
import serial
import pynmea2
from datetime import datetime
import math
import socket
import threading
import base64
import time


class GPSNode(Node):
    def __init__(self, node_name='gps_node'):
        super().__init__(node_name)
        
        # Declare parameters
        self.declare_parameter('serial_port', '/dev/ttyTHS1')  # Matches launch file default and docker-compose device mapping
        self.declare_parameter('baud_rate', 9600)  # Common GPS baud rate
        self.declare_parameter('frame_id', 'gps')
        self.declare_parameter('publish_rate', 10.0)
        self.declare_parameter('use_rtk', False)
        
        # NTRIP parameters
        self.declare_parameter('ntrip_server', '10.0.213.211')
        self.declare_parameter('ntrip_port', 2101)
        self.declare_parameter('ntrip_mountpoint', 'BASE')
        self.declare_parameter('ntrip_username', 'nfazio')
        self.declare_parameter('ntrip_password', '123456789')
        
        # Initialize variables
        self.serial_conn = None
        self.timer = None
        self.fix_pub = None
        self.velocity_pub = None
        self.nmea_pub = None
        self.sat_pub = None
        self.ntrip_socket = None
        self.ntrip_thread = None
        self.ntrip_running = False
        self.enabled = False
        
        # Subscribe to enable/disable commands
        self.enable_sub = self.create_subscription(
            Bool, 
            '/enable_gps', 
            self.on_enable_callback, 
            10
        )
        
        self.get_logger().info('GPS Node created (lifecycle)')
    
    def on_configure(self, state: State) -> TransitionCallbackReturn:
        """Configure the node - set up parameters and resources."""
        self.get_logger().info('Configuring GPS node...')
        
        # Get parameters
        self.serial_port = self.get_parameter('serial_port').value
        self.baud_rate = self.get_parameter('baud_rate').value
        self.frame_id = self.get_parameter('frame_id').value
        self.publish_rate = self.get_parameter('publish_rate').value
        self.use_rtk = self.get_parameter('use_rtk').value
        
        # NTRIP parameters
        self.ntrip_server = self.get_parameter('ntrip_server').value
        self.ntrip_port = self.get_parameter('ntrip_port').value
        self.ntrip_mountpoint = self.get_parameter('ntrip_mountpoint').value
        self.ntrip_username = self.get_parameter('ntrip_username').value
        self.ntrip_password = self.get_parameter('ntrip_password').value
        
        # Create lifecycle publishers
        self.fix_pub = self.create_lifecycle_publisher(NavSatFix, 'gps/fix', 10)
        self.velocity_pub = self.create_lifecycle_publisher(TwistStamped, 'gps/velocity', 10)
        self.nmea_pub = self.create_lifecycle_publisher(String, 'gps/nmea_sentence', 10)
        self.sat_pub = self.create_lifecycle_publisher(String, 'gps/satellites', 10)
        
        # Store last valid position and satellite count
        self.last_fix = NavSatFix()
        self.last_fix.header.frame_id = self.frame_id
        self.last_sat_count = 0
        
        self.get_logger().info('GPS node configured')
        return TransitionCallbackReturn.SUCCESS
    
    def on_activate(self, state: State) -> TransitionCallbackReturn:
        """Activate the node - start publishing and processing."""
        self.get_logger().info('Activating GPS node...')
        
        # Activate publishers
        self.fix_pub.on_activate(state)
        self.velocity_pub.on_activate(state)
        self.nmea_pub.on_activate(state)
        self.sat_pub.on_activate(state)
        
        # Connect to serial port
        self.connect_serial()
        
        # Create timer for reading GPS data
        timer_period = 1.0 / self.publish_rate
        self.timer = self.create_timer(timer_period, self.read_gps_data)
        
        # Start NTRIP if enabled
        if self.use_rtk:
            self.get_logger().info('RTK mode enabled')
            self.start_ntrip_client()
        
        self.enabled = True
        self.get_logger().info(f'GPS Node activated on {self.serial_port} @ {self.baud_rate} baud')
        return TransitionCallbackReturn.SUCCESS
    
    def on_deactivate(self, state: State) -> TransitionCallbackReturn:
        """Deactivate the node - stop publishing."""
        self.get_logger().info('Deactivating GPS node...')
        
        self.enabled = False
        
        # Stop NTRIP client
        self.stop_ntrip_client()
        
        # Destroy timer
        if self.timer:
            self.timer.cancel()
            self.timer = None
        
        # Close serial connection
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            self.get_logger().info('Serial connection closed')
        
        # Deactivate publishers
        self.fix_pub.on_deactivate(state)
        self.velocity_pub.on_deactivate(state)
        self.nmea_pub.on_deactivate(state)
        
        self.get_logger().info('GPS node deactivated')
        return TransitionCallbackReturn.SUCCESS
    
    def on_cleanup(self, state: State) -> TransitionCallbackReturn:
        """Cleanup resources."""
        self.get_logger().info('Cleaning up GPS node...')
        
        # Destroy publishers
        if self.fix_pub:
            self.destroy_publisher(self.fix_pub)
        if self.velocity_pub:
            self.destroy_publisher(self.velocity_pub)
        if self.nmea_pub:
            self.destroy_publisher(self.nmea_pub)
        
        self.get_logger().info('GPS node cleaned up')
        return TransitionCallbackReturn.SUCCESS
    
    def on_shutdown(self, state: State) -> TransitionCallbackReturn:
        """Shutdown the node."""
        self.get_logger().info('Shutting down GPS node...')
        self.stop_ntrip_client()
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
        return TransitionCallbackReturn.SUCCESS
    
    def on_enable_callback(self, msg: Bool):
        """Handle enable/disable commands from mode manager."""
        if msg.data and not self.enabled:
            # Enable GPS - transition to active
            self.get_logger().info('GPS enable requested')
            if self.get_current_state().label == 'inactive':
                self.trigger_activate()
        elif not msg.data and self.enabled:
            # Disable GPS - transition to inactive
            self.get_logger().info('GPS disable requested')
            if self.get_current_state().label == 'active':
                self.trigger_deactivate()
    
    def connect_serial(self):
        """Establish serial connection to GPS module."""
        try:
            self.serial_conn = serial.Serial(
                port=self.serial_port,
                baudrate=self.baud_rate,
                timeout=1.0,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE
            )
            self.get_logger().info(f'Connected to GPS on {self.serial_port}')
        except serial.SerialException as e:
            self.get_logger().error(f'Failed to open serial port: {e}')
            self.serial_conn = None
    
    def read_gps_data(self):
        """Read and parse GPS data from serial port."""
        if not self.enabled:
            return
            
        if self.serial_conn is None or not self.serial_conn.is_open:
            self.get_logger().warn('Serial connection not available, attempting reconnect...')
            self.connect_serial()
            return
        
        try:
            # Read line from serial
            if self.serial_conn.in_waiting > 0:
                line = self.serial_conn.readline().decode('ascii', errors='ignore').strip()
                
                if line.startswith('$'):
                    # Publish raw NMEA sentence
                    nmea_msg = String()
                    nmea_msg.data = line
                    self.nmea_pub.publish(nmea_msg)
                    
                    # Parse NMEA sentence
                    self.parse_nmea(line)
                    
        except serial.SerialException as e:
            self.get_logger().error(f'Serial read error: {e}')
            self.serial_conn = None
        except Exception as e:
            self.get_logger().error(f'Error reading GPS data: {e}')
    
    def parse_nmea(self, sentence):
        """Parse NMEA sentence and publish ROS messages."""
        try:
            msg = pynmea2.parse(sentence)
            
            # Handle different NMEA message types
            if isinstance(msg, pynmea2.types.talker.GGA):
                # Global Positioning System Fix Data
                self.handle_gga(msg)
            elif isinstance(msg, pynmea2.types.talker.RMC):
                # Recommended Minimum Navigation Information
                self.handle_rmc(msg)
            elif isinstance(msg, pynmea2.types.talker.VTG):
                # Track made good and Ground speed
                self.handle_vtg(msg)
                
        except pynmea2.ParseError as e:
            self.get_logger().debug(f'NMEA parse error: {e}')
        except Exception as e:
            self.get_logger().error(f'Error parsing NMEA: {e}')
    
    def handle_gga(self, msg):
        """Handle GGA (Fix Data) message."""
        if msg.latitude is None or msg.longitude is None:
            return
        
        fix = NavSatFix()
        fix.header.stamp = self.get_clock().now().to_msg()
        fix.header.frame_id = self.frame_id
        
        # Position
        fix.latitude = msg.latitude
        fix.longitude = msg.longitude
        fix.altitude = msg.altitude if msg.altitude else 0.0
        
        # Status
        fix.status.status = NavSatStatus.STATUS_NO_FIX
        if msg.gps_qual == 0:
            fix.status.status = NavSatStatus.STATUS_NO_FIX
        elif msg.gps_qual == 1:
            fix.status.status = NavSatStatus.STATUS_FIX
        elif msg.gps_qual == 2:
            fix.status.status = NavSatStatus.STATUS_SBAS_FIX
        elif msg.gps_qual in [4, 5]:  # RTK Fix or RTK Float
            fix.status.status = NavSatStatus.STATUS_GBAS_FIX
        
        fix.status.service = NavSatStatus.SERVICE_GPS
        
        # Covariance (based on HDOP if available)
        if msg.horizontal_dil:
            hdop = float(msg.horizontal_dil)
            fix.position_covariance[0] = (hdop * 2) ** 2
            fix.position_covariance[4] = (hdop * 2) ** 2
            fix.position_covariance[8] = (hdop * 4) ** 2
            fix.position_covariance_type = NavSatFix.COVARIANCE_TYPE_APPROXIMATED
        else:
            fix.position_covariance_type = NavSatFix.COVARIANCE_TYPE_UNKNOWN
        
        # Publish satellite count
        if msg.num_sats is not None:
            self.last_sat_count = int(msg.num_sats)
            sat_msg = String()
            sat_msg.data = str(self.last_sat_count)
            self.sat_pub.publish(sat_msg)
        
        self.last_fix = fix
        self.fix_pub.publish(fix)
        
        # Log RTK status
        if msg.gps_qual == 4:
            self.get_logger().info('RTK Fixed solution!')
        elif msg.gps_qual == 5:
            self.get_logger().debug('RTK Float solution')
    
    def handle_rmc(self, msg):
        """Handle RMC (Recommended Minimum) message."""
        if msg.latitude is None or msg.longitude is None:
            return
        
        # Update fix if we have valid data
        if msg.status == 'A':  # Active
            fix = NavSatFix()
            fix.header.stamp = self.get_clock().now().to_msg()
            fix.header.frame_id = self.frame_id
            
            fix.latitude = msg.latitude
            fix.longitude = msg.longitude
            fix.altitude = self.last_fix.altitude  # RMC doesn't have altitude
            
            fix.status.status = NavSatStatus.STATUS_FIX
            fix.status.service = NavSatStatus.SERVICE_GPS
            
            self.last_fix = fix
            self.fix_pub.publish(fix)
    
    def handle_vtg(self, msg):
        """Handle VTG (Velocity) message."""
        if msg.spd_over_grnd_kmph is None:
            return
        
        velocity = TwistStamped()
        velocity.header.stamp = self.get_clock().now().to_msg()
        velocity.header.frame_id = self.frame_id
        
        # Convert km/h to m/s
        speed_ms = float(msg.spd_over_grnd_kmph) / 3.6
        
        # Calculate velocity components if we have course
        if msg.true_track is not None:
            course_rad = math.radians(float(msg.true_track))
            velocity.twist.linear.x = speed_ms * math.cos(course_rad)
            velocity.twist.linear.y = speed_ms * math.sin(course_rad)
        else:
            velocity.twist.linear.x = speed_ms
        
        velocity.twist.linear.z = 0.0
        
        self.velocity_pub.publish(velocity)
    
    def start_ntrip_client(self):
        """Start NTRIP client thread to receive RTK corrections."""
        if not self.use_rtk:
            return
        
        self.get_logger().info(f'Starting NTRIP client: {self.ntrip_server}:{self.ntrip_port}/{self.ntrip_mountpoint}')
        self.ntrip_running = True
        self.ntrip_thread = threading.Thread(target=self.ntrip_client_loop, daemon=True)
        self.ntrip_thread.start()
    
    def ntrip_client_loop(self):
        """NTRIP client loop running in background thread."""
        reconnect_delay = 5
        
        while self.ntrip_running:
            try:
                self.get_logger().info('Connecting to NTRIP caster...')
                
                # Create socket connection
                self.ntrip_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.ntrip_socket.settimeout(10)
                self.ntrip_socket.connect((self.ntrip_server, self.ntrip_port))
                
                # Build NTRIP request
                auth_string = f"{self.ntrip_username}:{self.ntrip_password}"
                auth_bytes = auth_string.encode('ascii')
                auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
                
                request = (
                    f"GET /{self.ntrip_mountpoint} HTTP/1.1\r\n"
                    f"Host: {self.ntrip_server}\r\n"
                    f"Ntrip-Version: Ntrip/2.0\r\n"
                    f"User-Agent: NTRIP ROS2GPSClient/1.0\r\n"
                    f"Authorization: Basic {auth_b64}\r\n"
                    f"Connection: close\r\n"
                    f"\r\n"
                )
                
                # Send request
                self.ntrip_socket.send(request.encode())
                
                # Read response header
                response = b''
                while b'\r\n\r\n' not in response:
                    chunk = self.ntrip_socket.recv(1)
                    if not chunk:
                        raise Exception("Connection closed while reading header")
                    response += chunk
                
                response_str = response.decode('ascii', errors='ignore')
                
                if 'ICY 200 OK' in response_str or 'HTTP/1.1 200 OK' in response_str:
                    self.get_logger().info('NTRIP connection established successfully')
                else:
                    self.get_logger().error(f'NTRIP connection failed: {response_str}')
                    raise Exception(f"NTRIP error: {response_str}")
                
                # Receive and forward RTCM data
                self.ntrip_socket.settimeout(60)  # 60 second timeout for data
                bytes_received = 0
                
                while self.ntrip_running:
                    try:
                        data = self.ntrip_socket.recv(1024)
                        if not data:
                            self.get_logger().warn('NTRIP connection closed by server')
                            break
                        
                        bytes_received += len(data)
                        
                        # Forward RTCM corrections to GPS module
                        if self.serial_conn and self.serial_conn.is_open:
                            self.serial_conn.write(data)
                        
                        # Log progress periodically
                        if bytes_received % 10000 < 1024:
                            self.get_logger().debug(f'RTCM data received: {bytes_received} bytes')
                    
                    except socket.timeout:
                        self.get_logger().warn('NTRIP timeout - no data received')
                        break
                
            except Exception as e:
                self.get_logger().error(f'NTRIP error: {e}')
            
            finally:
                if self.ntrip_socket:
                    try:
                        self.ntrip_socket.close()
                    except:
                        pass
                    self.ntrip_socket = None
            
            if self.ntrip_running:
                self.get_logger().info(f'Reconnecting to NTRIP in {reconnect_delay} seconds...')
                time.sleep(reconnect_delay)
    
    def stop_ntrip_client(self):
        """Stop NTRIP client thread."""
        self.ntrip_running = False
        if self.ntrip_socket:
            try:
                self.ntrip_socket.close()
            except:
                pass
        if self.ntrip_thread:
            self.ntrip_thread.join(timeout=2)
    
    def destroy_node(self):
        """Clean up when node is destroyed."""
        self.stop_ntrip_client()
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            self.get_logger().info('Serial connection closed')
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    gps_node = GPSNode()
    
    # Configure and activate the lifecycle node
    gps_node.trigger_configure()
    gps_node.trigger_activate()
    
    try:
        rclpy.spin(gps_node)
    except KeyboardInterrupt:
        pass
    finally:
        gps_node.trigger_deactivate()
        gps_node.trigger_cleanup()
        gps_node.trigger_shutdown()
        gps_node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
