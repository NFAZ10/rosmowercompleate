# ROS Mower Web Control Server

## Quick Start

### Option 1: Run Web Server Directly (Recommended for Testing)

```bash
cd /mnt/nova_ssd/rosmowercompleate
./start-web-server.sh
```

Then open your browser to:
- **Local access**: http://localhost:8080
- **Remote access**: http://YOUR_ROBOT_IP:8080

### Option 2: Install as System Service (Runs Automatically)

```bash
cd /mnt/nova_ssd/rosmowercompleate
./install-web-server.sh
```

The web server will start automatically on boot.

## Features

### Web Interface

The control panel provides:

1. **Mode Control** - Switch between operational modes:
   - 💤 **IDLE** - All systems off (low power)
   - 🔋 **CHARGING** - Battery monitoring only
   - 🌱 **MOWING** - Full autonomous operation
   - ⚡ **FULL** - All systems enabled

2. **System Commands** - Execute docker-helper.sh commands:
   - 🚀 **Launch** - Start the robot system
   - 📊 **Status** - Check system status
   - 🛰️ **GPS** - GPS information
   - 🔄 **Restart** - Restart Docker container
   - ⏹️ **Stop** - Stop Docker container

3. **Live Status** - Real-time monitoring:
   - Container status
   - ROS bridge connection
   - Current mode
   - Command output logs

## API Endpoints

The web server provides REST API endpoints:

- `GET /` - Main control page
- `GET /api/status` - System status (JSON)
- `GET /api/command/<cmd>` - Execute docker-helper.sh command (stat, gps, launch, etc.)
- `GET /api/docker/start` - Start Docker container
- `GET /api/docker/stop` - Stop Docker container
- `GET /api/docker/restart` - Restart Docker container

## Managing the Service

```bash
# Check service status
sudo systemctl status rosmower-web

# Start service
sudo systemctl start rosmower-web

# Stop service
sudo systemctl stop rosmower-web

# Restart service
sudo systemctl restart rosmower-web

# View logs
sudo journalctl -u rosmower-web -f
```

## Accessing from Mobile/Other Devices

1. Find your robot's IP address:
   ```bash
   hostname -I
   ```

2. Open browser on any device on same network:
   ```
   http://YOUR_ROBOT_IP:8080
   ```

3. The page works on phones, tablets, and computers!

## Firewall Configuration

If you can't access from other devices, open port 8080:

```bash
sudo ufw allow 8080/tcp
```

## Troubleshooting

**Can't access web page:**
- Check if server is running: `ps aux | grep web_server.py`
- Check port 8080: `sudo netstat -tlnp | grep 8080`
- Check firewall: `sudo ufw status`

**Commands don't work:**
- Ensure docker-helper.sh has execute permissions
- Check user has docker access: `groups | grep docker`
- View server logs: `sudo journalctl -u rosmower-web -f`

**ROS connection fails:**
- Ensure Docker container is running
- Verify rosbridge is active: `docker exec rosmower_robot ros2 node list | grep rosbridge`
- Check websocket port 9090 is accessible

## Architecture

```
┌─────────────┐
│   Browser   │
│  (Port 80)  │
└──────┬──────┘
       │ HTTP
       ▼
┌─────────────────┐
│  Flask Server   │
│   (Port 8080)   │
└────┬──────┬─────┘
     │      │
     │      │ WebSocket (9090)
     │      ▼
     │  ┌──────────────┐
     │  │  ROS Bridge  │
     │  │  in Docker   │
     │  └──────────────┘
     │
     │ Execute commands
     ▼
┌──────────────────┐
│ docker-helper.sh │
│  (System cmds)   │
└──────────────────┘
```

## Security Note

This web server runs with your user privileges and can execute system commands. Only use on trusted networks or add authentication if exposed to internet.
