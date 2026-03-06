#!/usr/bin/env python3
"""
ROS Mower Web Server
Serves the mode control interface and provides API for system control
"""

from flask import Flask, render_template, jsonify, send_from_directory
from flask_cors import CORS
import subprocess
import os
import signal
import threading
import time
import socket

app = Flask(__name__, 
            template_folder='/mnt/nova_ssd/rosmowercompleate/src/rosmower/web',
            static_folder='/mnt/nova_ssd/rosmowercompleate/src/rosmower/web')
CORS(app)

# Path to docker-helper.sh
DOCKER_HELPER = '/mnt/nova_ssd/rosmowercompleate/docker-helper.sh'

# Track running processes
running_processes = {}
process_lock = threading.Lock()

def get_ros_container():
    """Get the name of the running ROS container (prefer rosmower_launch, then rosmower_robot, then others)."""
    for container in ['rosmower_launch_noarm', 'rosmower_launch', 'rosmower_robot', 'rosmower_gps_zones', 'rosmower_rtk', 'rosmower_bridge']:
        result = subprocess.run(
            ['docker', 'ps', '--filter', f'name={container}', '--format', '{{.Names}}'],
            capture_output=True, text=True
        )
        if result.stdout.strip():
            return container
    return 'rosmower_robot'  # Default fallback

def get_device_ip():
    """Get the primary IP address of the device."""
    try:
        # Create a socket to determine the primary network interface IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            # Doesn't need to be reachable, just used to determine route
            s.connect(('10.254.254.254', 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip
    except Exception:
        return '127.0.0.1'

@app.route('/')
def index():
    """Serve the main control page."""
    return send_from_directory('/mnt/nova_ssd/rosmowercompleate/src/rosmower/web', 'mode_control.html')

@app.route('/camera')
def camera_control():
    """Serve the camera control page."""
    return send_from_directory('/mnt/nova_ssd/rosmowercompleate/src/rosmower/web', 'camera_control.html')

@app.route('/status')
def status_page():
    """Serve the status monitoring page."""
    return send_from_directory('/mnt/nova_ssd/rosmowercompleate/src/rosmower/web', 'status.html')

@app.route('/zones')
def zone_manager_page():
    """Serve the zone manager page."""
    return send_from_directory('/mnt/nova_ssd/rosmowercompleate/src/rosmower/web', 'zone_manager.html')

@app.route('/zones/recorder')
def zone_recorder_page():
    """Serve the zone recorder page."""
    return send_from_directory('/mnt/nova_ssd/rosmowercompleate/src/rosmower/web', 'zone_recorder.html')

@app.route('/api/ip')
def get_ip():
    """Get the device IP address."""
    return jsonify({'ip': get_device_ip()})

@app.route('/api/status')
def get_status():
    """Get system status."""
    try:
        container = get_ros_container()
        # Check if Docker container is running
        result = subprocess.run(
            ['docker', 'ps', '--filter', f'name={container}', '--format', '{{.Status}}'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        container_running = 'Up' in result.stdout
        
        # Check ROS bridge
        rosbridge_running = False
        if container_running:
            try:
                ros_check = subprocess.run(
                    ['docker', 'exec', container, 'bash', '-c', 
                     'source /opt/ros/humble/setup.bash && ros2 node list 2>/dev/null | grep -q rosbridge_websocket && echo "running" || echo "not running"'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                rosbridge_running = 'running' in ros_check.stdout
            except:
                pass
        
        return jsonify({
            'container_running': container_running,
            'rosbridge_running': rosbridge_running,
            'container_status': result.stdout.strip() if container_running else 'Not running'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/command/<cmd>')
def execute_command(cmd):
    """Execute docker-helper.sh commands."""
    allowed_commands = ['stat', 'gps', 'launch', 'bridge', 'rqt', 'stop', 'restart', 'cleanup']
    
    if cmd not in allowed_commands:
        return jsonify({'error': f'Command "{cmd}" not allowed'}), 400
    
    try:
        # Special handling for launch and bridge - run in background
        if cmd in ['launch', 'bridge']:
            with process_lock:
                # Kill any existing process of same type
                if cmd in running_processes:
                    old_proc = running_processes[cmd]
                    if old_proc.poll() is None:
                        return jsonify({'error': f'{cmd.title()} already running', 'status': 'running'}), 409
                
                # Clean up old dev containers to free camera devices
                cleanup = subprocess.run(
                    ['docker', 'ps', '-q', '--filter', 'name=rosmowercompleate-dev-run'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if cleanup.stdout.strip():
                    # Stop all old dev containers
                    container_ids = cleanup.stdout.strip().split('\n')
                    for container_id in container_ids:
                        subprocess.run(['docker', 'stop', container_id], timeout=10)
                
                # Start new process
                process = subprocess.Popen(
                    [DOCKER_HELPER, cmd, '-d'],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd='/mnt/nova_ssd/rosmowercompleate'
                )
                running_processes[cmd] = process
                
                return jsonify({
                    'status': 'started',
                    'message': f'{cmd.title()} command started (PID: {process.pid})',
                    'command': cmd
                })
        
        # Special cleanup command to stop all dev containers
        if cmd == 'cleanup':
            cleanup = subprocess.run(
                ['docker', 'ps', '-q', '--filter', 'name=rosmowercompleate-dev-run'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if cleanup.stdout.strip():
                container_ids = cleanup.stdout.strip().split('\n')
                stopped = []
                for container_id in container_ids:
                    result = subprocess.run(['docker', 'stop', container_id], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        stopped.append(container_id)
                
                return jsonify({
                    'status': 'completed',
                    'message': f'Stopped {len(stopped)} dev containers',
                    'containers': stopped
                })
            else:
                return jsonify({
                    'status': 'completed',
                    'message': 'No dev containers running'
                })
        
        # For other commands, run synchronously with timeout
        result = subprocess.run(
            [DOCKER_HELPER, cmd],
            capture_output=True,
            text=True,
            timeout=30,
            cwd='/mnt/nova_ssd/rosmowercompleate'
        )
        
        return jsonify({
            'status': 'completed',
            'command': cmd,
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        })
        
    except subprocess.TimeoutExpired:
        return jsonify({'error': f'Command "{cmd}" timed out'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/docker/start')
def docker_start():
    """Start Docker container."""
    try:
        result = subprocess.run(
            ['docker', 'start', 'rosmower_robot'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        return jsonify({
            'status': 'success' if result.returncode == 0 else 'failed',
            'output': result.stdout + result.stderr
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/docker/stop')
def docker_stop():
    """Stop Docker container."""
    try:
        result = subprocess.run(
            ['docker', 'stop', 'rosmower_robot'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return jsonify({
            'status': 'success' if result.returncode == 0 else 'failed',
            'output': result.stdout + result.stderr
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/docker/restart')
def docker_restart():
    """Restart Docker container."""
    try:
        result = subprocess.run(
            ['docker', 'restart', 'rosmower_robot'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        return jsonify({
            'status': 'success' if result.returncode == 0 else 'failed',
            'output': result.stdout + result.stderr
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/process/<name>/status')
def process_status(name):
    """Check status of a background process."""
    with process_lock:
        if name not in running_processes:
            return jsonify({'status': 'not_found'}), 404
        
        proc = running_processes[name]
        if proc.poll() is None:
            return jsonify({'status': 'running', 'pid': proc.pid})
        else:
            stdout, stderr = proc.communicate()
            return jsonify({
                'status': 'completed',
                'returncode': proc.returncode,
                'stdout': stdout[:1000] if stdout else '',  # Limit output
                'stderr': stderr[:1000] if stderr else ''
            })

@app.route('/api/container/stop/<container_name>')
def stop_container(container_name):
    """Stop a specific container by name pattern."""
    try:
        # Validate container name pattern
        allowed_patterns = ['rosmower_launch', 'rosmower_bridge', 'rosmower_status', 'rosmower_dev_shell', 'rosmower_rqt']
        
        if container_name not in allowed_patterns:
            return jsonify({'error': f'Container pattern "{container_name}" not allowed'}), 400
        
        # Find containers matching the pattern
        result = subprocess.run(
            ['docker', 'ps', '-q', '--filter', f'name={container_name}'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        container_ids = result.stdout.strip().split('\n')
        container_ids = [cid.strip() for cid in container_ids if cid.strip()]
        
        if not container_ids:
            return jsonify({
                'status': 'not_found',
                'message': f'No containers found matching "{container_name}"'
            })
        
        # Stop each container
        stopped = []
        for container_id in container_ids:
            stop_result = subprocess.run(
                ['docker', 'stop', container_id],
                capture_output=True,
                text=True,
                timeout=10
            )
            if stop_result.returncode == 0:
                stopped.append(container_id)
        
        return jsonify({
            'status': 'success',
            'message': f'Stopped {len(stopped)} container(s)',
            'containers': stopped
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ros/nodes')
def get_ros_nodes():
    """Get list of running ROS nodes and topics."""
    try:
        container = get_ros_container()
        # Check if Docker container is running
        container_check = subprocess.run(
            ['docker', 'ps', '--filter', f'name={container}', '--format', '{{.Status}}'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        container_running = 'Up' in container_check.stdout
        
        if not container_running:
            return jsonify({
                'container_running': False,
                'nodes': [],
                'topics': [],
                'error': 'Docker container is not running'
            })
        
        # Get ROS nodes
        nodes = []
        try:
            node_result = subprocess.run(
                ['docker', 'exec', container, 'bash', '-c', 
                 'source /opt/ros/humble/setup.bash && ros2 node list'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if node_result.returncode == 0:
                nodes = [n.strip() for n in node_result.stdout.strip().split('\n') if n.strip()]
        except Exception as e:
            print(f'Error getting nodes: {e}')
        
        # Get ROS topics
        topics = []
        try:
            topic_result = subprocess.run(
                ['docker', 'exec', container, 'bash', '-c', 
                 'source /opt/ros/humble/setup.bash && ros2 topic list'],
                capture_output=True,
                text=True,
                timeout=10
            )
            if topic_result.returncode == 0:
                topics = [t.strip() for t in topic_result.stdout.strip().split('\n') if t.strip()]
        except Exception as e:
            print(f'Error getting topics: {e}')
        
        return jsonify({
            'container_running': container_running,
            'nodes': nodes,
            'topics': topics,
            'node_count': len(nodes),
            'topic_count': len(topics)
        })
        
    except Exception as e:
        return jsonify({'error': str(e), 'container_running': False}), 500

# Zone Management API Endpoints
@app.route('/api/zones', methods=['GET'])
def get_zones():
    """Get all zones from the zones directory."""
    import yaml
    import json
    from pathlib import Path
    
    zones_dir = Path('/mnt/nova_ssd/rosmowercompleate/zones')
    zones = []
    
    try:
        if zones_dir.exists():
            for file_path in zones_dir.glob('*.yaml'):
                try:
                    with open(file_path, 'r') as f:
                        zone_data = yaml.safe_load(f)
                        # Convert to ROS message format
                        zone = {
                            'id': zone_data.get('id', file_path.stem),
                            'name': zone_data.get('name', file_path.stem),
                            'priority': zone_data.get('priority', 5),
                            'enabled': zone_data.get('enabled', True),
                            'coverage_percent': zone_data.get('coverage_percent', 0.0),
                            'polygon': {
                                'header': {
                                    'frame_id': zone_data.get('frame_id', 'map')
                                },
                                'polygon': {
                                    'points': zone_data.get('vertices', [])
                                }
                            }
                        }
                        zones.append(zone)
                except Exception as e:
                    print(f"Error loading zone {file_path}: {e}")
        
        return jsonify({
            'success': True,
            'zones': zones,
            'count': len(zones)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/zones/save', methods=['POST'])
def save_zone():
    """Save a zone to disk."""
    import yaml
    from pathlib import Path
    from flask import request
    
    try:
        zone_data = request.json
        
        if not zone_data or 'id' not in zone_data:
            return jsonify({'success': False, 'message': 'Invalid zone data'}), 400
        
        zone_id = zone_data['id']
        zones_dir = Path('/mnt/nova_ssd/rosmowercompleate/zones')
        zones_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = zones_dir / f'{zone_id}.yaml'
        
        # Convert from web format to YAML format
        yaml_data = {
            'id': zone_data.get('id'),
            'name': zone_data.get('name'),
            'priority': zone_data.get('priority', 5),
            'enabled': zone_data.get('enabled', True),
            'coverage_percent': zone_data.get('coverage_percent', 0.0),
            'frame_id': zone_data.get('frame_id', 'map'),
            'vertices': zone_data.get('vertices', [])
        }
        
        with open(file_path, 'w') as f:
            yaml.dump(yaml_data, f, default_flow_style=False)
        
        return jsonify({
            'success': True,
            'message': f'Zone {zone_data.get("name")} saved successfully',
            'file': str(file_path)
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/zones/delete/<zone_id>', methods=['DELETE'])
def delete_zone(zone_id):
    """Delete a zone from disk."""
    from pathlib import Path
    
    try:
        zones_dir = Path('/mnt/nova_ssd/rosmowercompleate/zones')
        file_path = zones_dir / f'{zone_id}.yaml'
        
        if not file_path.exists():
            return jsonify({'success': False, 'message': f'Zone {zone_id} not found'}), 404
        
        file_path.unlink()
        
        return jsonify({
            'success': True,
            'message': f'Zone {zone_id} deleted successfully'
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/battery/status', methods=['GET'])
def get_battery_status():
    """Get current battery status from ROS topics."""
    try:
        # Try to get battery percentage
        result = subprocess.run(
            [DOCKER_HELPER, 'exec', 'bash', '-c',
             'timeout 2 ros2 topic echo /percent std_msgs/msg/Float32 --once 2>/dev/null || echo "data: -1.0"'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        # Parse the output
        import re
        match = re.search(r'data:\s*([\d.]+)', result.stdout)
        percentage = float(match.group(1)) if match else -1.0
        
        # Get battery state if battery monitor is running
        state_result = subprocess.run(
            [DOCKER_HELPER, 'exec', 'bash', '-c',
             'timeout 2 ros2 topic echo /battery/state std_msgs/msg/String --once 2>/dev/null || echo "data: UNKNOWN"'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        state_match = re.search(r'data:\s*["\']?(\w+)["\']?', state_result.stdout)
        state = state_match.group(1) if state_match else 'UNKNOWN'
        
        return jsonify({
            'success': True,
            'percentage': percentage,
            'state': state,
            'low_battery': percentage > 0 and percentage < 25.0,
            'critical_battery': percentage > 0 and percentage < 15.0
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# Zone Recording API Endpoints
@app.route('/api/zone/record/start', methods=['POST'])
def start_zone_recording():
    """Start recording a zone boundary via GPS."""
    from flask import request
    try:
        data = request.json or {}
        zone_name = data.get('zone_name', 'New Zone')
        priority = data.get('priority', 5)
        use_visual_odom = data.get('use_visual_odometry', False)
        
        # Call ROS service with workspace sourced
        container = get_ros_container()
        service_call = f"source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && timeout 8 ros2 service call /zone/record/start rosmower_msgs/srv/StartZoneRecording '{{zone_name: \"{zone_name}\", priority: {priority}, use_visual_odometry: {str(use_visual_odom).lower()}}}'"
        
        result = subprocess.run(
            ['docker', 'exec', container, 'bash', '-c', service_call],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0 and 'success: true' in result.stdout.lower():
            return jsonify({
                'success': True,
                'message': f'Started recording zone: {zone_name}',
                'zone_name': zone_name
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to start recording',
                'error': result.stderr
            }), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/zone/record/stop', methods=['POST'])
def stop_zone_recording():
    """Stop recording and save zone."""
    from flask import request
    try:
        data = request.json or {}
        save_zone = data.get('save_zone', True)
        auto_close = data.get('auto_close', True)
        simplify = data.get('simplify', True)
        tolerance = data.get('simplification_tolerance', 0.3)
        
        # Call ROS service with workspace sourced
        container = get_ros_container()
        result = subprocess.run(
            ['docker', 'exec', container, 'bash', '-c',
             f'source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && timeout 8 ros2 service call /zone/record/stop rosmower_msgs/srv/StopZoneRecording \'{{save_zone: {str(save_zone).lower()}, auto_close: {str(auto_close).lower()}, simplify: {str(simplify).lower()}, simplification_tolerance: {tolerance}}}\''],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            # Parse output for success/failure
            import re
            success_match = re.search(r'success:\s*(true|false)', result.stdout, re.IGNORECASE)
            message_match = re.search(r'message:\s*["\']?([^"\'\\n]+)["\']?', result.stdout)
            
            success = success_match and success_match.group(1).lower() == 'true' if success_match else False
            message = message_match.group(1) if message_match else 'Recording stopped'
            
            return jsonify({
                'success': success,
                'message': message,
                'raw_output': result.stdout[:500]  # First 500 chars for debugging
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to stop recording',
                'error': result.stderr
            }), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/zone/record/pause', methods=['POST'])
def pause_zone_recording():
    """Pause zone recording."""
    try:
        # Call ROS service
        container = get_ros_container()
        result = subprocess.run(
            ['docker', 'exec', container, 'bash', '-c',
             'source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && timeout 6 ros2 service call /zone/record/control rosmower_msgs/srv/ControlZoneRecording "{command: 0}"'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and 'success: true' in result.stdout.lower():
            return jsonify({
                'success': True,
                'message': 'Recording paused'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to pause recording',
                'error': result.stderr
            }), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/zone/record/resume', methods=['POST'])
def resume_zone_recording():
    """Resume zone recording."""
    try:
        # Call ROS service
        container = get_ros_container()
        result = subprocess.run(
            ['docker', 'exec', container, 'bash', '-c',
             'source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && timeout 6 ros2 service call /zone/record/control rosmower_msgs/srv/ControlZoneRecording "{command: 1}"'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and 'success: true' in result.stdout.lower():
            return jsonify({
                'success': True,
                'message': 'Recording resumed'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to resume recording',
                'error': result.stderr
            }), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/zone/record/cancel', methods=['POST'])
def cancel_zone_recording():
    """Cancel zone recording."""
    try:
        # Call ROS service
        container = get_ros_container()
        result = subprocess.run(
            ['docker', 'exec', container, 'bash', '-c',
             'source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && timeout 6 ros2 service call /zone/record/control rosmower_msgs/srv/ControlZoneRecording "{command: 2}"'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and 'success: true' in result.stdout.lower():
            return jsonify({
                'success': True,
                'message': 'Recording cancelled'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to cancel recording',
                'error': result.stderr
            }), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/zone/record/status', methods=['GET'])
def get_zone_record_status():
    """Get current zone recording status."""
    try:
        container = get_ros_container()
        import re
        import math
        
        # Get GPS fix data to determine quality (with longer timeout for Zenoh)
        gps_result = subprocess.run(
            ['docker', 'exec', container, 'bash', '-c',
             'source /opt/ros/humble/setup.bash && timeout 8 ros2 topic echo /gps/fix sensor_msgs/msg/NavSatFix --once 2>/dev/null'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        gps_quality = 0
        gps_accuracy = 999.0
        
        if gps_result.returncode == 0 and gps_result.stdout.strip():
            # Parse GPS status
            status_match = re.search(r'status:\s*(-?\d+)', gps_result.stdout)
            cov_match = re.search(r'position_covariance:\s*\n-\s*([\d.]+)', gps_result.stdout)
            
            if status_match:
                gps_status = int(status_match.group(1))
                # Map status to quality: -1=no fix, 0=fix, 1=SBAS, 2=RTK
                if gps_status == -1:
                    gps_quality = 0  # No fix
                    gps_accuracy = 999.0
                elif gps_status == 0:
                    gps_quality = 2  # 3D fix
                    gps_accuracy = 1.5  # Typical GPS accuracy
                elif gps_status == 1:
                    gps_quality = 2  # SBAS fix
                    gps_accuracy = 1.0
                elif gps_status == 2:
                    gps_quality = 4  # RTK fix
                    gps_accuracy = 0.05
            
            # Override accuracy if covariance is available and non-zero
            if cov_match:
                cov_value = float(cov_match.group(1))
                if cov_value > 0:
                    # Covariance is in meters^2, so take sqrt for accuracy
                    gps_accuracy = math.sqrt(cov_value)
        
        # Get full zone recording status (waypoints, distance, area, state)
        status_result = subprocess.run(
            ['docker', 'exec', container, 'bash', '-c',
             'source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && timeout 3 ros2 topic echo /zone/record/status --once 2>/dev/null'],
            capture_output=True,
            text=True,
            timeout=5
        )

        waypoint_count = 0
        distance_traveled = 0.0
        estimated_area = 0.0
        zone_name = ''
        state = 0
        state_str = 'IDLE'
        status_message = ''

        if status_result.stdout.strip():
            out = status_result.stdout
            m = re.search(r'state:\s*(\d+)', out)
            if m:
                state = int(m.group(1))
                state_str = ['IDLE', 'RECORDING', 'PAUSED'].get(state, 'IDLE') if isinstance(['IDLE', 'RECORDING', 'PAUSED'], dict) else {0: 'IDLE', 1: 'RECORDING', 2: 'PAUSED'}.get(state, 'IDLE')
            m = re.search(r'zone_name:\s*(.+)', out)
            if m:
                zone_name = m.group(1).strip()
            m = re.search(r'waypoint_count:\s*(\d+)', out)
            if m:
                waypoint_count = int(m.group(1))
            m = re.search(r'distance_traveled:\s*([\d.]+)', out)
            if m:
                distance_traveled = float(m.group(1))
            m = re.search(r'estimated_area:\s*([\d.]+)', out)
            if m:
                estimated_area = float(m.group(1))
            m = re.search(r'status_message:\s*(.+)', out)
            if m:
                status_message = m.group(1).strip()
            # Override GPS accuracy from status topic if available
            m = re.search(r'gps_accuracy:\s*([\d.]+)', out)
            if m:
                val = float(m.group(1))
                if val > 0:
                    gps_accuracy = val
            m = re.search(r'gps_quality:\s*(\d+)', out)
            if m:
                gps_quality = int(m.group(1))

        if not status_message:
            status_message = f'GPS: {["No Fix", "2D Fix", "3D Fix", "RTK Float", "RTK Fixed"][min(gps_quality, 4)]}'

        return jsonify({
            'success': True,
            'state': state,
            'state_str': state_str,
            'zone_name': zone_name,
            'waypoint_count': waypoint_count,
            'distance_traveled': distance_traveled,
            'estimated_area': estimated_area,
            'gps_quality': gps_quality,
            'gps_accuracy': gps_accuracy,
            'status_message': status_message
        })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def cleanup():
    """Clean up background processes on shutdown."""
    with process_lock:
        for name, proc in running_processes.items():
            if proc.poll() is None:
                print(f'Terminating {name} process (PID: {proc.pid})')
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()

# ========== ROUTE MANAGEMENT API ==========

@app.route('/routes')
def route_manager_page():
    """Serve the route manager page."""
    return send_from_directory('/mnt/nova_ssd/rosmowercompleate/src/rosmower/web', 'zone_routes.html')

@app.route('/api/routes/list', methods=['GET'])
def list_routes():
    """List all available routes."""
    try:
        import yaml
        from pathlib import Path
        
        routes_dir = Path('/ws/routes')
        if not routes_dir.exists():
            return jsonify({'routes': []})
        
        routes = []
        for route_file in routes_dir.glob('*.yaml'):
            try:
                with open(route_file, 'r') as f:
                    route_data = yaml.safe_load(f)
                    routes.append(route_data)
            except Exception as e:
                print(f"Error loading route {route_file}: {e}")
        
        return jsonify({'routes': routes})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/routes/record/start', methods=['POST'])
def start_route_recording():
    """Start recording a new route."""
    try:
        from flask import request
        data = request.get_json()
        
        # Call ROS service via docker exec
        result = subprocess.run(
            ['docker', 'exec', 'rosmower_robot', 'bash', '-c',
             'source /ws/install/setup.bash && ros2 service call /route/record/start std_srvs/srv/Trigger'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Store route parameters in a temp file for route_manager to pick up
        # (In production, use custom service type with parameters)
        import json
        params_file = Path('/ws/routes/.recording_params.json')
        params_file.parent.mkdir(parents=True, exist_ok=True)
        with open(params_file, 'w') as f:
            json.dump(data, f)
        
        return jsonify({
            'success': True,
            'message': 'Route recording started',
            'parameters': data
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/routes/record/stop', methods=['POST'])
def stop_route_recording():
    """Stop route recording and save."""
    try:
        result = subprocess.run(
            ['docker', 'exec', 'rosmower_robot', 'bash', '-c',
             'source /ws/install/setup.bash && ros2 service call /route/record/stop std_srvs/srv/Trigger'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        return jsonify({
            'success': True,
            'message': 'Route recording stopped and saved'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/routes/record/pause', methods=['POST'])
def pause_route_recording():
    """Pause route recording."""
    try:
        result = subprocess.run(
            ['docker', 'exec', 'rosmower_robot', 'bash', '-c',
             'source /ws/install/setup.bash && ros2 service call /route/record/pause std_srvs/srv/Trigger'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        return jsonify({'success': True, 'message': 'Route recording paused'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/routes/record/resume', methods=['POST'])
def resume_route_recording():
    """Resume route recording."""
    try:
        result = subprocess.run(
            ['docker', 'exec', 'rosmower_robot', 'bash', '-c',
             'source /ws/install/setup.bash && ros2 service call /route/record/resume std_srvs/srv/Trigger'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        return jsonify({'success': True, 'message': 'Route recording resumed'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/routes/record/cancel', methods=['POST'])
def cancel_route_recording():
    """Cancel route recording without saving."""
    try:
        result = subprocess.run(
            ['docker', 'exec', 'rosmower_robot', 'bash', '-c',
             'source /ws/install/setup.bash && ros2 service call /route/record/cancel std_srvs/srv/Trigger'],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        return jsonify({'success': True, 'message': 'Route recording cancelled'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/routes/delete/<route_id>', methods=['DELETE'])
def delete_route(route_id):
    """Delete a route by ID."""
    try:
        from pathlib import Path
        routes_dir = Path('/ws/routes')
        
        # Find route file
        deleted = False
        for route_file in routes_dir.glob('*.yaml'):
            import yaml
            with open(route_file, 'r') as f:
                data = yaml.safe_load(f)
                if data.get('route_id') == route_id:
                    route_file.unlink()
                    deleted = True
                    break
        
        if deleted:
            return jsonify({'success': True, 'message': f'Route {route_id} deleted'})
        else:
            return jsonify({'success': False, 'message': 'Route not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/routes/status', methods=['GET'])
def get_route_recording_status():
    """Get current route recording status."""
    try:
        # This would subscribe to /route/recording/status topic
        # For now, return placeholder
        return jsonify({
            'is_recording': False,
            'is_paused': False,
            'waypoints_collected': 0,
            'distance_meters': 0.0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/zones/graph', methods=['GET'])
def get_zone_graph():
    """Get zone connectivity graph."""
    try:
        # This would subscribe to /zones/graph topic
        # For now, generate from zones and routes
        import yaml
        from pathlib import Path
        
        zones_dir = Path('/ws/zones')
        routes_dir = Path('/ws/routes')
        
        nodes = []
        edges = []
        
        # Load zones
        if zones_dir.exists():
            for zone_file in zones_dir.glob('*.yaml'):
                with open(zone_file, 'r') as f:
                    zone_data = yaml.safe_load(f)
                    nodes.append({
                        'zone_id': zone_data.get('id', zone_file.stem),
                        'zone_name': zone_data.get('name', zone_file.stem),
                        'priority': zone_data.get('priority', 5)
                    })
        
        # Load routes
        if routes_dir.exists():
            for route_file in routes_dir.glob('*.yaml'):
                with open(route_file, 'r') as f:
                    route_data = yaml.safe_load(f)
                    edges.append({
                        'from_zone_id': route_data.get('from_zone_id'),
                        'to_zone_id': route_data.get('to_zone_id'),
                        'route_id': route_data.get('route_id'),
                        'distance_meters': route_data.get('total_distance_meters', 0),
                        'bidirectional': route_data.get('bidirectional', True)
                    })
        
        return jsonify({'nodes': nodes, 'edges': edges})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/zones/update_priority', methods=['POST'])
def update_zone_priority():
    """Update zone priority."""
    try:
        from flask import request
        import yaml
        from pathlib import Path
        
        data = request.get_json()
        zone_id = data.get('zone_id')
        priority = data.get('priority')
        
        zones_dir = Path('/ws/zones')
        zone_file = zones_dir / f'{zone_id}.yaml'
        
        if not zone_file.exists():
            return jsonify({'success': False, 'message': 'Zone not found'}), 404
        
        # Load, update, and save
        with open(zone_file, 'r') as f:
            zone_data = yaml.safe_load(f)
        
        zone_data['priority'] = priority
        
        with open(zone_file, 'w') as f:
            yaml.safe_dump(zone_data, f, default_flow_style=False)
        
        return jsonify({'success': True, 'message': f'Priority updated to {priority}'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    import atexit
    atexit.register(cleanup)
    
    print('=' * 60)
    print('ROS Mower Web Server Starting')
    print('=' * 60)
    print('Access the control panel at:')
    print('  http://localhost:8080')
    print('  http://<your-robot-ip>:8080')
    print('=' * 60)
    
    # Run server
    app.run(host='0.0.0.0', port=8080, debug=False, threaded=True)
