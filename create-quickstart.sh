#!/bin/bash
# Update the QUICKSTART guide with web server information

cat > QUICKSTART_WEB_CONTROL.md << 'EOF'
# Quick Start: Web Control Panel

## 🌐 Always-On Web Interface

Your ROS Mower now has a web-based control panel that's always available!

## Start the Web Server

### Quick Start (Manual)
```bash
cd /mnt/nova_ssd/rosmowercompleate
./start-web-server.sh
```

### Install as Service (Auto-start on boot)
```bash
cd /mnt/nova_ssd/rosmowercompleate
./install-web-server.sh
```

## Access the Control Panel

Open your browser to:
- **On the robot**: http://localhost:8080
- **From another device**: http://10.31.18.195:8080
  (Use your robot's actual IP address)

## What You Can Do

### 1. Switch Modes in Real-Time
Click any mode button:
- 💤 **IDLE** - Everything off (standby)
- 🔋 **CHARGING** - Battery monitoring only
- 🌱 **MOWING** - Full autonomous operation
- ⚡ **FULL** - All systems enabled

### 2. Execute System Commands
- 🚀 **Launch** - Start the entire robot system
- 📊 **Status** - View system status
- 🛰️ **GPS** - Check GPS information
- 🔄 **Restart** - Restart Docker container
- ⏹️ **Stop** - Stop Docker container

### 3. Monitor System Status
The page shows real-time:
- Container running status
- ROS bridge connection
- Current operational mode
- Command execution logs

## Mobile Access

The control panel works perfectly on phones and tablets!

1. Connect your phone to the same network as your robot
2. Open browser and go to: `http://YOUR_ROBOT_IP:8080`
3. Control your robot from anywhere on your network!

## Current Status

✅ **Web server is running at**: http://10.31.18.195:8080
- Container status checks every 5 seconds
- Full ROS integration via rosbridge
- Command execution with live feedback

## Architecture

```
Your Browser (Phone/Laptop)
        ↓
   Web Server (Port 8080)
   ├── Mode Control → ROS Bridge (Port 9090) → Mode Manager
   └── System Commands → docker-helper.sh → Docker Container
```

## Next Steps

1. Open http://10.31.18.195:8080 in your browser
2. Click "🚀 Launch" to start the system
3. Switch between modes as needed
4. Monitor everything from one interface!

## See Also

- Full documentation: `WEB_SERVER_README.md`
- Mode control details: `MODE_CONTROL_README.md`
- Docker helper: `DOCKER_README.md`
EOF

echo "✅ Created QUICKSTART_WEB_CONTROL.md"
