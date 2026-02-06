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

## What You Can Do

### 1. Switch Modes in Real-Time
- 💤 **IDLE** - Everything off
- 🔋 **CHARGING** - Battery monitoring only
- 🌱 **MOWING** - Full autonomous
- ⚡ **FULL** - All systems enabled

### 2. Execute System Commands
- 🚀 **Launch** - Start the robot
- 📊 **Status** - View status
- 🛰️ **GPS** - GPS info
- 🔄 **Restart** - Restart container
- ⏹️ **Stop** - Stop container

### 3. Monitor System
- Container status (live)
- ROS bridge connection
- Current mode
- Command logs

## Mobile Friendly

Works on phones and tablets! Just go to:
`http://YOUR_ROBOT_IP:8080`
