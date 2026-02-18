# Zenoh Router Auto-Start Setup

## Overview
This guide sets up the Zenoh router to automatically start at boot and restart if it crashes, using systemd.

## Quick Install

```bash
# Run the installer (requires sudo)
sudo ./install-zenoh-service.sh
```

## What It Does

✅ **Auto-start at boot** - Zenoh router starts automatically when system boots  
✅ **Auto-restart on failure** - If Zenoh crashes, systemd restarts it after 10 seconds  
✅ **Health monitoring** - Verifies container is running after start  
✅ **Proper cleanup** - Stops existing containers before starting new one  

## Service Management

### Check Status
```bash
sudo systemctl status zenoh-router
```

### Start Manually
```bash
sudo systemctl start zenoh-router
```

### Stop
```bash
sudo systemctl stop zenoh-router
```

### Restart
```bash
sudo systemctl restart zenoh-router
```

### View Logs (Live)
```bash
sudo journalctl -u zenoh-router -f
```

### View Recent Logs
```bash
sudo journalctl -u zenoh-router -n 50
```

### Disable Auto-Start
```bash
sudo systemctl disable zenoh-router
```

### Re-Enable Auto-Start
```bash
sudo systemctl enable zenoh-router
```

## Verify It's Working

### 1. Check the service started:
```bash
sudo systemctl status zenoh-router
```

Expected output:
```
● zenoh-router.service - Zenoh Router for ROS2 Multi-Robot Communication
     Loaded: loaded (/etc/systemd/system/zenoh-router.service; enabled)
     Active: active (running) since...
```

### 2. Check the Docker container is running:
```bash
docker ps --filter "name=rosmower_zenoh"
```

Expected output:
```
CONTAINER ID   IMAGE             COMMAND                  CREATED          STATUS
abc123...      rosmower:latest   "bash -c 'export ZEN…"   10 seconds ago   Up 9 seconds
```

### 3. Check Zenoh router logs:
```bash
docker logs rosmower_zenoh
```

Expected output:
```
Started Zenoh router with id fa674b7a07a43a8cbff7dfb3c369719c
```

## Configuration

Zenoh router uses the configuration file:
```
/mnt/nova_ssd/rosmowercompleate/zenoh-router.json5
```

**Current settings:**
- Mode: `router`
- Listen: `tcp/0.0.0.0:7447` (all interfaces)
- Connect: `tcp/63.133.235.92:7447` (external router)
- Multicast: Enabled on `224.0.0.224:7446`

To modify configuration:
1. Edit `zenoh-router.json5`
2. Restart service: `sudo systemctl restart zenoh-router`

## Troubleshooting

### Service won't start
```bash
# Check logs for errors
sudo journalctl -u zenoh-router -n 100

# Try manual start to see detailed output
./docker-helper.sh zenoh
```

### Container keeps restarting
```bash
# Check Docker logs
docker logs rosmower_zenoh

# Check if config file is valid
cat zenoh-router.json5
```

### Port already in use (7447)
```bash
# Find what's using the port
sudo netstat -tulpn | grep 7447

# Stop conflicting process
sudo systemctl stop <conflicting-service>
```

### Changes to docker-helper.sh not working
```bash
# Reload systemd after changes
sudo systemctl daemon-reload
sudo systemctl restart zenoh-router
```

## Integration with ROS2

The Zenoh router enables:
- **Low-bandwidth ROS2 communication** over WAN/internet
- **Multi-robot coordination** across different networks
- **Edge-to-cloud connectivity** for telemetry and control

### Using Zenoh with ROS2

Set environment variable before launching ROS nodes:
```bash
export RMW_IMPLEMENTATION=rmw_zenoh_cpp
ros2 launch rosmower launch_robot.launch.py
```

This is already configured in `docker-compose.yml` for all containers.

## File Locations

- **Systemd service**: `/etc/systemd/system/zenoh-router.service`
- **Config file**: `/mnt/nova_ssd/rosmowercompleate/zenoh-router.json5`
- **Launcher script**: `/mnt/nova_ssd/rosmowercompleate/docker-helper.sh`
- **Installer**: `/mnt/nova_ssd/rosmowercompleate/install-zenoh-service.sh`

## Uninstall

To remove the auto-start service:

```bash
# Stop and disable
sudo systemctl stop zenoh-router
sudo systemctl disable zenoh-router

# Remove service file
sudo rm /etc/systemd/system/zenoh-router.service

# Reload systemd
sudo systemctl daemon-reload
```

The Docker container and config files remain intact - you can still run manually with:
```bash
./docker-helper.sh zenoh -d
```

## Notes

- The service runs as your user (not root) for Docker compatibility
- Auto-restart waits 10 seconds between attempts
- Health check waits up to 30 seconds for container to start
- Container is removed automatically on stop (--rm flag in docker-helper.sh)

---

**Created:** 2026-02-11  
**For:** ROSmower autonomous robot platform  
**Uses:** docker-helper.sh zenoh command with systemd wrapper
