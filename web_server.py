#!/usr/bin/env python3
"""
ROS Mower Web Server
Serves the mode control interface and provides API for system control
"""

from flask import Flask, render_template, jsonify, send_from_directory, request
from flask_cors import CORS
import errno
import subprocess
import os
import signal
import threading
import time
import socket
from pathlib import Path

app = Flask(__name__, 
            template_folder='/mnt/nova_ssd/rosmowercompleate/src/rosmower/web',
            static_folder='/mnt/nova_ssd/rosmowercompleate/src/rosmower/web')
CORS(app)

# Path to docker-helper.sh
DOCKER_HELPER = '/mnt/nova_ssd/rosmowercompleate/docker-helper.sh'
OPEN_MOWER_ROOT = Path('/home/nfazio/openmower-docker/openmower-humble')
OPEN_MOWER_SERVICE = 'open_mower_humble'
OPENMOWER_MAIN_CONTAINER = 'open_mower_humble'

# Track running processes
running_processes = {}
process_lock = threading.Lock()

PORT_WAIT_TIMEOUT_SECONDS = 30

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

def get_web_port():
    """Return the configured web server port."""
    raw_port = os.environ.get('ROSMOWER_WEB_PORT', '80').strip()
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise ValueError(f'Invalid ROSMOWER_WEB_PORT: {raw_port!r}') from exc

    if not 1 <= port <= 65535:
        raise ValueError(f'ROSMOWER_WEB_PORT must be between 1 and 65535, got {port}')

    return port

def wait_for_port_release(host, port, timeout_seconds=PORT_WAIT_TIMEOUT_SECONDS):
    """Wait for the listen port to become available during boot-time races."""
    deadline = time.monotonic() + timeout_seconds

    while True:
        probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
            return
        except OSError as exc:
            if exc.errno != errno.EADDRINUSE:
                raise

            remaining = max(0, int(deadline - time.monotonic()))
            if remaining == 0:
                raise TimeoutError(
                    f'Port {port} is still in use after waiting {timeout_seconds} seconds'
                ) from exc

            print(f'Port {port} is busy, waiting for it to become available ({remaining}s left)...')
            time.sleep(1)
        finally:
            probe.close()

def run_open_mower_compose(args, timeout=30):
    """Run docker compose commands for the Open Mower stack."""
    if not OPEN_MOWER_ROOT.exists():
        raise FileNotFoundError(f'Open Mower directory not found at {OPEN_MOWER_ROOT}')

    return subprocess.run(
        ['docker', 'compose', *args],
        cwd=str(OPEN_MOWER_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout
    )

def get_open_mower_status():
    """Return status for the Open Mower runtime by querying the container directly."""
    status = {
        'available': OPEN_MOWER_ROOT.exists(),
        'compose_dir': str(OPEN_MOWER_ROOT),
        'service': OPEN_MOWER_SERVICE,
        'running': False,
        'container_name': None,
        'container_status': 'Not running',
        'foxglove_ws_url': f'http://{get_device_ip()}:9091',
        'control_topic': '/cmd_vel',
        'key_topics': [],
        'warnings': [],
        'recent_logs': [],
    }

    if not status['available']:
        status['warnings'].append(f'Open Mower directory not found at {OPEN_MOWER_ROOT}')
        return status

    try:
        ps_result = subprocess.run(
            ['docker', 'ps', '--filter', f'name={OPENMOWER_MAIN_CONTAINER}',
             '--format', '{{.Names}}\t{{.Status}}'],
            capture_output=True, text=True, timeout=5
        )
        lines = [l.strip() for l in ps_result.stdout.splitlines() if l.strip()]
        if lines:
            parts = lines[0].split('\t')
            container_status = parts[1] if len(parts) > 1 else 'Unknown'
            status.update({
                'running': 'Up' in container_status,
                'container_name': parts[0],
                'container_status': container_status,
            })

        if status['running']:
            topic_result = subprocess.run(
                ['docker', 'exec', OPENMOWER_MAIN_CONTAINER, 'bash', '-lc',
                 'source /opt/ros/humble/setup.bash 2>/dev/null; '
                 'source /opt/ws/install/local_setup.bash 2>/dev/null; '
                 'timeout 4 ros2 topic list 2>/dev/null'],
                capture_output=True, text=True, timeout=8
            )
            if topic_result.returncode == 0:
                available_topics = {l.strip() for l in topic_result.stdout.splitlines() if l.strip()}
                for topic in ['/cmd_vel', '/map_grid', '/mowing_map', '/odometry/filtered/map', '/tf', '/tf_static']:
                    if topic in available_topics:
                        status['key_topics'].append(topic)

            log_result = subprocess.run(
                ['docker', 'logs', '--no-color', '--tail', '20', OPENMOWER_MAIN_CONTAINER],
                capture_output=True, text=True, timeout=10
            )
            if log_result.returncode == 0:
                combined = log_result.stdout + log_result.stderr
                recent_logs = [l for l in combined.splitlines() if l.strip()]
                status['recent_logs'] = recent_logs[-20:]
                status['warnings'] = [
                    l for l in status['recent_logs']
                    if 'Timed out waiting for transform' in l or '[ERROR]' in l or '[FATAL]' in l
                ][-5:]

    except Exception as exc:
        status['warnings'].append(str(exc))

    return status

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

@app.route('/open-mower')
@app.route('/zones')
def zone_manager_page():
    """Serve the Open Mower companion control page."""
    return send_from_directory('/mnt/nova_ssd/rosmowercompleate/src/rosmower/web', 'open_mower_control.html')

@app.route('/zones/recorder')
def zone_recorder_page():
    """Legacy route redirected to the Open Mower companion control page."""
    return send_from_directory('/mnt/nova_ssd/rosmowercompleate/src/rosmower/web', 'open_mower_control.html')

@app.route('/mission-setup')
def mission_setup_page():
    """Serve the mission setup page (dock position, zones, mission params)."""
    return send_from_directory('/mnt/nova_ssd/rosmowercompleate/src/rosmower/web', 'mission_setup.html')

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

@app.route('/api/open-mower/status', methods=['GET'])
def get_open_mower_companion_status():
    """Return status for the Open Mower companion planner stack."""
    status = get_open_mower_status()
    return jsonify({'success': True, **status})

@app.route('/api/open-mower/<action>', methods=['POST'])
def control_open_mower_companion(action):
    """Start, stop, or restart the Open Mower planner stack."""
    compose_actions = {
        'start':   ['-f', 'docker-compose.yaml', '-f', 'docker-compose.ui.yml', 'up', '-d'],
        'stop':    ['-f', 'docker-compose.yaml', '-f', 'docker-compose.ui.yml', 'stop'],
        'restart': ['-f', 'docker-compose.yaml', '-f', 'docker-compose.ui.yml', 'restart'],
    }

    if action not in compose_actions:
        return jsonify({'success': False, 'message': f'Unsupported action: {action}'}), 400

    try:
        result = run_open_mower_compose(compose_actions[action], timeout=180)
        status = get_open_mower_status()
        success = result.returncode == 0
        message = {
            'start':   'Open Mower started',
            'stop':    'Open Mower stopped',
            'restart': 'Open Mower restarted',
        }[action]

        return jsonify({
            'success': success,
            'action': action,
            'message': message if success else (result.stderr or result.stdout or f'Failed to {action} Open Mower'),
            'stdout': result.stdout[-4000:],
            'stderr': result.stderr[-4000:],
            'status': status,
        }), (200 if success else 500)
    except Exception as exc:
        return jsonify({'success': False, 'message': str(exc)}), 500

@app.route('/api/command/<cmd>')
def execute_command(cmd):
    """Execute docker-helper.sh commands."""
    allowed_commands = ['stat', 'gps', 'launch', 'bridge', 'rqt', 'stop', 'restart', 'cleanup', 'mission']
    
    if cmd not in allowed_commands:
        return jsonify({'error': f'Command "{cmd}" not allowed'}), 400
    
    try:
        # Special handling for launch, bridge, and mission - run in background
        if cmd in ['launch', 'bridge', 'mission']:
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
        EXCLUDED_ZONE_FILES = {'dock.yaml', 'mission_params.yaml'}
        if zones_dir.exists():
            for file_path in sorted(zones_dir.glob('*.yaml')):
                if file_path.name in EXCLUDED_ZONE_FILES:
                    continue
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

# ── Dock API ──────────────────────────────────────────────────────────────────

DOCK_FILE = Path('/mnt/nova_ssd/rosmowercompleate/zones/dock.yaml')
MISSION_PARAMS_FILE = Path('/mnt/nova_ssd/rosmowercompleate/src/openmower_mission/config/mission_params.yaml')

@app.route('/api/dock', methods=['GET'])
def get_dock():
    """Return current dock position from dock.yaml."""
    import yaml
    try:
        if not DOCK_FILE.exists():
            return jsonify({'success': True, 'dock': None, 'message': 'No dock file found'})
        with open(DOCK_FILE, 'r') as f:
            data = yaml.safe_load(f)
        return jsonify({'success': True, 'dock': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dock/save', methods=['POST'])
def save_dock():
    """Write dock position to dock.yaml. Accepts map-frame x/y or GPS lat/lon (or both)."""
    import yaml, math
    try:
        body = request.json or {}
        has_xy  = 'x' in body and 'y' in body
        has_gps = 'lat' in body and 'lon' in body
        if not has_xy and not has_gps:
            return jsonify({'success': False, 'message': 'Provide x+y (map frame) or lat+lon (GPS)'}), 400

        DOCK_FILE.parent.mkdir(parents=True, exist_ok=True)

        # Preserve any existing fields
        existing = {}
        if DOCK_FILE.exists():
            with open(DOCK_FILE, 'r') as f:
                existing = yaml.safe_load(f) or {}

        if has_xy:
            existing['frame_id'] = body.get('frame_id', existing.get('frame_id', 'map'))
            existing['x']   = round(float(body['x']), 4)
            existing['y']   = round(float(body['y']), 4)
            existing['yaw'] = round(float(body.get('yaw', existing.get('yaw', 0.0))), 4)
        if has_gps:
            existing['lat'] = round(float(body['lat']), 8)
            existing['lon'] = round(float(body['lon']), 8)
            if 'alt' in body:
                existing['alt'] = round(float(body['alt']), 3)

        with open(DOCK_FILE, 'w') as f:
            yaml.dump(existing, f, default_flow_style=False)
        return jsonify({'success': True, 'message': 'Dock position saved', 'dock': existing})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dock/command', methods=['POST'])
def dock_command():
    """Publish a command to /dock/command ROS topic."""
    try:
        body = request.json
        cmd = (body or {}).get('command', 'SET_DOCK_HERE').strip().upper()
        allowed = {'SET_DOCK_HERE', 'SET_DOCK_GPS', 'RETURN_TO_DOCK', 'CLEAR_DOCK'}
        if cmd not in allowed:
            return jsonify({'success': False, 'message': f'Unknown command: {cmd}'}), 400
        container = get_ros_container()
        result = subprocess.run(
            ['docker', 'exec', container, 'bash', '-c',
             f'source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && '
             f'ros2 topic pub --once /dock/command std_msgs/msg/String "{{data: \'{cmd}\'}}"'],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            return jsonify({'success': True, 'message': f'Sent: {cmd}'})
        return jsonify({'success': False, 'message': result.stderr or result.stdout}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/zones/<zone_id>', methods=['PATCH'])
def update_zone(zone_id):
    """Patch a single zone's enabled/priority/name fields."""
    import yaml
    try:
        body = request.json or {}
        zones_dir = Path('/mnt/nova_ssd/rosmowercompleate/zones')
        file_path = zones_dir / f'{zone_id}.yaml'
        if not file_path.exists():
            return jsonify({'success': False, 'message': f'Zone {zone_id} not found'}), 404
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        for field in ('enabled', 'priority', 'name'):
            if field in body:
                data[field] = body[field]
        with open(file_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False)
        return jsonify({'success': True, 'message': f'Zone {zone_id} updated', 'zone': data})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/mission/params', methods=['GET'])
def get_mission_params():
    """Return editable mission parameters."""
    import yaml
    EDITABLE_KEYS = [
        'stripe_width_m', 'overlap_m', 'approach_angle_deg', 'waypoint_spacing_m',
        'waypoint_goal_tolerance_m', 'stuck_timeout_sec', 'max_recovery_attempts',
        'battery_return_threshold_pct', 'path_generation_timeout_sec',
        'dock_staging_dist_m', 'loop_hz',
    ]
    try:
        if not MISSION_PARAMS_FILE.exists():
            return jsonify({'success': False, 'message': 'mission_params.yaml not found'}), 404
        with open(MISSION_PARAMS_FILE, 'r') as f:
            full = yaml.safe_load(f)
        params = full.get('/**', {}).get('ros__parameters', {})
        return jsonify({'success': True, 'params': {k: params[k] for k in EDITABLE_KEYS if k in params}})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/mission/params', methods=['POST'])
def save_mission_params():
    """Save updated mission parameters back to mission_params.yaml."""
    import yaml
    ALLOWED_KEYS = {
        'stripe_width_m', 'overlap_m', 'approach_angle_deg', 'waypoint_spacing_m',
        'waypoint_goal_tolerance_m', 'stuck_timeout_sec', 'max_recovery_attempts',
        'battery_return_threshold_pct', 'path_generation_timeout_sec',
        'dock_staging_dist_m', 'loop_hz',
    }
    try:
        updates = request.json or {}
        invalid = set(updates.keys()) - ALLOWED_KEYS
        if invalid:
            return jsonify({'success': False, 'message': f'Unknown params: {invalid}'}), 400
        with open(MISSION_PARAMS_FILE, 'r') as f:
            full = yaml.safe_load(f)
        params = full.setdefault('/**', {}).setdefault('ros__parameters', {})
        for k, v in updates.items():
            params[k] = v
        with open(MISSION_PARAMS_FILE, 'w') as f:
            yaml.dump(full, f, default_flow_style=False)
        return jsonify({'success': True, 'message': 'Mission parameters saved'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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
def _ros_srv_ok(stdout: str) -> bool:
    """
    ROS2 Humble service call output can be YAML ('success: true') or Python repr
    ('success=True'). Accept both.
    """
    lower = stdout.lower()
    return 'success=true' in lower or 'success: true' in lower


def _ensure_zone_recorder_running(container: str) -> tuple[bool, str]:
    """
    Check if zone_recorder node is running; auto-start it if not.
    Returns (success, message).
    """
    check = subprocess.run(
        ['docker', 'exec', container, 'bash', '-c',
         'source /opt/ros/humble/setup.bash && '
         'ros2 service list 2>/dev/null | grep -q /zone/record/start && echo READY'],
        capture_output=True, text=True, timeout=8
    )
    if 'READY' in check.stdout:
        return True, 'already running'

    # Node not running — launch it in the background inside the container
    subprocess.Popen(
        ['docker', 'exec', container, 'bash', '-c',
         'source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && '
         'ros2 run rosmower zone_recorder.py '
         '--ros-args --log-level warn '
         '-p gps_accuracy_threshold:=5.0 '
         '-p waypoint_min_distance:=0.5 '
         '-p simplification_tolerance:=0.3 '
         '-p publish_rate:=2.0 '
         '-p gps_topic:=/gps/fix'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

    # Wait up to 6 seconds for the service to become available
    for _ in range(12):
        time.sleep(0.5)
        probe = subprocess.run(
            ['docker', 'exec', container, 'bash', '-c',
             'source /opt/ros/humble/setup.bash && '
             'ros2 service list 2>/dev/null | grep -q /zone/record/start && echo READY'],
            capture_output=True, text=True, timeout=5
        )
        if 'READY' in probe.stdout:
            return True, 'started'

    return False, 'zone_recorder node failed to start — check that rosmower package is built in the container'


@app.route('/api/zone/record/start', methods=['POST'])
def start_zone_recording():
    """Start recording a zone boundary via GPS. Auto-starts zone_recorder node if needed."""
    from flask import request
    try:
        data = request.json or {}
        zone_name = data.get('zone_name', 'New Zone')
        priority = data.get('priority', 5)
        use_visual_odom = data.get('use_visual_odometry', False)

        container = get_ros_container()

        # Ensure the zone_recorder node is running before calling its service
        node_ok, node_msg = _ensure_zone_recorder_running(container)
        if not node_ok:
            return jsonify({
                'success': False,
                'message': f'Zone recorder node not available: {node_msg}',
                'hint': 'Run: docker exec <container> ros2 run rosmower zone_recorder.py'
            }), 503

        service_call = (
            f"source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && "
            f"timeout 8 ros2 service call /zone/record/start "
            f"rosmower_msgs/srv/StartZoneRecording "
            f"'{{zone_name: \"{zone_name}\", priority: {priority}, "
            f"use_visual_odometry: {str(use_visual_odom).lower()}}}'"
        )

        result = subprocess.run(
            ['docker', 'exec', container, 'bash', '-c', service_call],
            capture_output=True, text=True, timeout=12
        )

        if result.returncode == 0 and _ros_srv_ok(result.stdout):
            return jsonify({
                'success': True,
                'message': f'Started recording zone: {zone_name}',
                'zone_name': zone_name,
                'node_status': node_msg
            })
        else:
            # Extract the actual message from the service response
            import re
            msg_match = re.search(r"message='?([^',\)]+)'?", result.stdout)
            svc_msg = msg_match.group(1).strip() if msg_match else None
            return jsonify({
                'success': False,
                'message': svc_msg or 'Failed to start recording',
                'raw': (result.stderr or result.stdout or '').strip()[:200]
            }), 409 if svc_msg and 'already' in svc_msg.lower() else 500

    except subprocess.TimeoutExpired:
        return jsonify({
            'success': False,
            'message': 'Timed out waiting for zone recorder — GPS may be unavailable',
            'hint': 'Check GPS fix with: GET /api/zone/record/status'
        }), 504
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/zone/record/stop', methods=['POST'])
def stop_zone_recording():
    """Stop recording and save zone."""
    from flask import request
    import re
    try:
        data = request.json or {}
        save_zone = data.get('save_zone', True)
        auto_close = data.get('auto_close', True)
        simplify = data.get('simplify', True)
        tolerance = data.get('simplification_tolerance', 0.3)

        container = get_ros_container()
        result = subprocess.run(
            ['docker', 'exec', container, 'bash', '-c',
             f'source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && '
             f'timeout 8 ros2 service call /zone/record/stop '
             f'rosmower_msgs/srv/StopZoneRecording '
             f"'{{save_zone: {str(save_zone).lower()}, auto_close: {str(auto_close).lower()}, "
             f"simplify: {str(simplify).lower()}, simplification_tolerance: {tolerance}}}'"],
            capture_output=True, text=True, timeout=12
        )

        if result.returncode == 0:
            # Handle both YAML ('success: true') and Python repr ('success=True') output
            success = _ros_srv_ok(result.stdout)
            message_match = re.search(r'message[=:]\s*["\']?([^"\'=\n,)]+)', result.stdout, re.IGNORECASE)
            message = message_match.group(1).strip() if message_match else 'Recording stopped'
            return jsonify({'success': success, 'message': message,
                            'raw_output': result.stdout[:500]})
        else:
            err = (result.stderr or result.stdout or '').strip()[:300]
            return jsonify({'success': False,
                            'message': 'Zone recorder not running — start recording first',
                            'error': err}), 503

    except subprocess.TimeoutExpired:
        return jsonify({'success': False,
                        'message': 'Service timed out — zone recorder may have crashed'}), 504
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def _zone_control_call(command_int: int, command_name: str):
    """Shared helper for pause/resume/cancel service calls."""
    container = get_ros_container()
    result = subprocess.run(
        ['docker', 'exec', container, 'bash', '-c',
         f'source /opt/ros/humble/setup.bash && source /ws/install/setup.bash && '
         f'timeout 6 ros2 service call /zone/record/control '
         f'rosmower_msgs/srv/ControlZoneRecording "{{command: {command_int}}}"'],
        capture_output=True, text=True, timeout=8
    )
    if result.returncode == 0 and _ros_srv_ok(result.stdout):
        return jsonify({'success': True, 'message': f'Recording {command_name}'})
    err = (result.stderr or result.stdout or '').strip()[:200]
    return jsonify({'success': False,
                    'message': f'Failed to {command_name} — zone recorder may not be recording',
                    'error': err}), 503


@app.route('/api/zone/record/pause', methods=['POST'])
def pause_zone_recording():
    """Pause zone recording."""
    try:
        return _zone_control_call(0, 'paused')
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'message': 'Service timed out'}), 504
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/zone/record/resume', methods=['POST'])
def resume_zone_recording():
    """Resume zone recording."""
    try:
        return _zone_control_call(1, 'resumed')
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'message': 'Service timed out'}), 504
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/zone/record/cancel', methods=['POST'])
def cancel_zone_recording():
    """Cancel zone recording without saving."""
    try:
        return _zone_control_call(2, 'cancelled')
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'message': 'Service timed out'}), 504
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
    """Legacy route redirected to the Open Mower companion control page."""
    return send_from_directory('/mnt/nova_ssd/rosmowercompleate/src/rosmower/web', 'open_mower_control.html')

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

    try:
        web_port = get_web_port()
        wait_for_port_release('0.0.0.0', web_port)
    except (ValueError, TimeoutError) as exc:
        print(f'Failed to start web server: {exc}')
        raise SystemExit(1) from exc

    port_suffix = '' if web_port == 80 else f':{web_port}'

    print('=' * 60)
    print('ROS Mower Web Server Starting')
    print('=' * 60)
    print('Access the control panel at:')
    print(f'  http://localhost{port_suffix}')
    print(f'  http://<your-robot-ip>{port_suffix}')
    print('=' * 60)

    # Run server
    app.run(host='0.0.0.0', port=web_port, debug=False, threaded=True)
