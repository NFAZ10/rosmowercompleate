# RTK GPS Integration - Complete Setup

## Summary
RTK GPS system integrated into ROS2 workspace with LC29HDA rover module. The system runs RTKLIB rtkrcv inside Docker and publishes GPS data to ROS2 topics.

## Files Moved to Docker Workspace

### RTKLIB Binary
- **Location**: `src/gps_rtk/rtklib/rtkrcv`
- **Source**: ~/RTKLIB-2.4.3/app/consapp/rtkrcv/gcc/rtkrcv (demo5 b34L)

### Configuration Files
- **Location**: `src/gps_rtk/config/`
  - `rover.conf` - RTKLIB RTK rover configuration
  - `configure_lc29h_ubx.sh` - Switch LC29HDA to UBX format
  - `configure_lc29h_nmea.sh` - Revert LC29HDA to NMEA format

### Launch File
- **Location**: `src/gps_rtk/launch/rtklib.launch.py`
- **Function**: Starts RTKLIB rtkrcv + ROS2 GPS node

## Docker Updates

### Dockerfile
- Added `ros-humble-nmea-navsat-driver` package (line 81)
- Ensures nmea_navsat_driver is available in all containers
- **IMAGE REBUILT**: February 2, 2026 - nmea_navsat_driver now installed permanently
- Fixed GitHub CLI Copilot extension installation (commented out - requires auth)

### docker-compose.yml
- Added `/dev/ttyTHS1` device mapping to dev container (line 106)
- GPS rover accessible from inside Docker

### Rebuild Status
✅ **Docker image successfully rebuilt with GPS dependencies**
- No need to manually install ros-humble-nmea-navsat-driver anymore
- Launch file now works immediately in fresh containers
- Build log: `docker_build_gps.log`

## Hardware Setup

### LC29HDA Rover Module
- **Connection**: 40-pin GPIO header → /dev/ttyTHS1
- **Baud Rate**: 115200
- **Current Format**: NMEA (text)
- **RTK Format**: UBX (binary) - use configure_lc29h_ubx.sh

### Base Station
- **IP**: 10.0.213.211
- **Port**: 5016
- **Format**: RTCM3 corrections

## Usage

### Quick Start (Docker)
```bash
# Start Docker dev container
cd /mnt/nova_ssd/rosmowercompleate
./docker-helper.sh dev

# In container - launch GPS
source install/setup.bash
ros2 launch gps_rtk rtklib.launch.py
```

**Note**: Ensure /dev/ttyTHS1 is not in use by other processes before launching.

### Option 1: Use Current NMEA GPS (Testing)
```bash
# In Docker dev container
cd /ws_dev
source install/setup.bash
ros2 launch gps_rtk rtklib.launch.py start_rtklib:=false

# Rover outputs NMEA, no RTK corrections
# Good for testing GPS is working
```

### Option 2: Full RTK Mode (At Final Location)
```bash
# 1. Configure rover for UBX format (one-time)
sudo /share/gps_rtk/rtklib/configure_lc29h_ubx.sh

# 2. Rebuild workspace to get new config
cd /ws_dev
colcon build --packages-select gps_rtk
source install/setup.bash

# 3. Launch RTK GPS with RTKLIB
ros2 launch gps_rtk rtklib.launch.py

# RTKLIB will:
# - Read UBX data from /dev/ttyTHS1
# - Get RTCM3 corrections from base (10.0.213.211:5016)
# - Compute RTK position
# - Output NMEA to TCP port 9001
# - ROS2 node publishes to /gps/fix
```

## ROS2 Topics Published

- `/gps/fix` - sensor_msgs/NavSatFix with RTK quality
- `/gps/vel` - geometry_msgs/TwistStamped
- `/gps/time` - sensor_msgs/TimeReference

## RTK Fix Quality (NavSatFix.status.status)

- `0` = No Fix / Standard GPS (~2-5m accuracy)
- `1` = DGPS / RTK Float (~0.1-1m accuracy)
- `2` = RTK Fixed (~0.01-0.05m accuracy) ✨

## Monitoring

```bash
# Check GPS fix status
ros2 topic echo /gps/fix --field status.status

# Monitor RTK position
ros2 topic echo /gps/fix

# Check RTKLIB status (if running separately)
echo "status" | nc localhost 2101
```

## Troubleshooting

### "Device or resource busy" Error
If you see this when accessing /dev/ttyTHS1:
1. Another process has the device open (possibly from a previous test)
2. Find process: `sudo lsof /dev/ttyTHS1` or `sudo fuser /dev/ttyTHS1`
3. Kill the process or reboot

### GPS Not Working
1. Check rover is powered and connected to /dev/ttyTHS1
2. Verify device access: `ls -l /dev/ttyTHS1`
3. Test data flow: `sudo cat /dev/ttyTHS1 | head -10`

### No RTK Fix
1. Verify base station connectivity: `nc 10.0.213.211 5016 | xxd | head -20`
2. Check rover is in UBX mode (not NMEA)
3. Ensure clear sky view (GPS needs satellites)
4. Check RTKLIB status in launch output

### Docker Can't Access Device
1. Verify `/dev/ttyTHS1` exists on host
2. Check docker-compose.yml has device mapping
3. Run with `--privileged` flag (already set in compose file)

## Next Steps

1. **Test indoors with NMEA**: Verify GPS hardware works
2. **Move outdoors**: Get satellite lock
3. **At final location**: 
   - Configure rover for UBX
   - Verify base station connection
   - Launch full RTK system
4. **Integrate with navigation**: Use /gps/fix in robot_localization

## Files Reference

- Launch: `src/gps_rtk/launch/rtklib.launch.py`
- Config: `src/gps_rtk/config/rover.conf`
- Binary: `src/gps_rtk/rtklib/rtkrcv`
- Setup: `src/gps_rtk/setup.py`
- Docker: `Dockerfile` (line 81)
- Compose: `docker-compose.yml` (line 106)
