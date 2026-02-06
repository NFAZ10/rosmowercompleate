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

app = Flask(__name__, 
            template_folder='/mnt/nova_ssd/rosmowercompleate/src/rosmower/web',
            static_folder='/mnt/nova_ssd/rosmowercompleate/src/rosmower/web')
CORS(app)

# Path to docker-helper.sh
DOCKER_HELPER = '/mnt/nova_ssd/rosmowercompleate/docker-helper.sh'

# Track running processes
running_processes = {}
process_lock = threading.Lock()

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

@app.route('/api/status')
def get_status():
    """Get system status."""
    try:
        # Check if Docker container is running
        result = subprocess.run(
            ['docker', 'ps', '--filter', 'name=rosmower_robot', '--format', '{{.Status}}'],
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
                    ['docker', 'exec', 'rosmower_robot', 'bash', '-c', 
                     'ros2 node list 2>/dev/null | grep -q rosbridge_websocket && echo "running" || echo "not running"'],
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
        # Check if Docker container is running
        container_check = subprocess.run(
            ['docker', 'ps', '--filter', 'name=rosmower_robot', '--format', '{{.Status}}'],
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
                ['docker', 'exec', 'rosmower_robot', 'bash', '-c', 
                 'source /opt/ros/humble/setup.bash && ros2 node list'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if node_result.returncode == 0:
                nodes = [n.strip() for n in node_result.stdout.strip().split('\n') if n.strip()]
        except Exception as e:
            print(f'Error getting nodes: {e}')
        
        # Get ROS topics
        topics = []
        try:
            topic_result = subprocess.run(
                ['docker', 'exec', 'rosmower_robot', 'bash', '-c', 
                 'source /opt/ros/humble/setup.bash && ros2 topic list'],
                capture_output=True,
                text=True,
                timeout=5
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
