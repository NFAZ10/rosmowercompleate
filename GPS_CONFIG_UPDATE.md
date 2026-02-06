# GPS Configuration Update Summary

## Changes Made

Updated: `src/gps_rtk/config/gps_params.yaml`

```yaml
gps_node:
  ros__parameters:
    serial_port: '/dev/ttyTHS1'  # Changed from /dev/ttyACM0 → Jetson GPIO UART
    baud_rate: 115200            # Changed from 9600 → LC29H default
    frame_id: 'gps'
    publish_rate: 10.0
    use_rtk: false
```

## What Was Wrong

1. **Wrong Port**: Config had `/dev/ttyACM0` (that's your Ardupilot/Arduino)
2. **Wrong Baud**: Was set to 9600, should be 115200 for LC29H
3. **Multiple Nodes Running**: 3 GPS nodes are running simultaneously

## Next Steps - YOU NEED TO DO THIS

The GPS nodes are running as **root inside Docker**, so you need to restart them:

### Option 1: Restart via Docker
```bash
# Find your ROS docker container
docker ps

# Restart it
docker restart <container_name>
```

### Option 2: Kill nodes from inside Docker
```bash
# Enter docker container
docker exec -it <container_name> bash

# Kill GPS nodes
kill 22473 23982 24558

# Restart GPS node
ros2 launch gps_rtk gps.launch.py
```

### Option 3: Rebuild and restart (recommended)
```bash
# Rebuild the workspace so new config is copied
cd /mnt/nova_ssd/rosmowercompleate
colcon build --packages-select gps_rtk --symlink-install

# Then restart the container or the node
```

## Testing After Restart

Check if GPS is working:
```bash
# Monitor GPS topics
ros2 topic echo /gps/fix
ros2 topic echo /gps/nmea_sentence

# Check GPS node logs
ros2 node info /gps_node

# Test port directly
python3 test_gps_standalone.py /dev/ttyTHS1 115200
```

## Important Notes

- **Antenna**: GPS still needs antenna connected with clear sky view
- **Device**: Confirmed you're on Jetson Orin Nano, not Raspberry Pi
- **Port**: `/dev/ttyTHS1` is the Jetson GPIO UART (not ttyACM0 or ttyAMA0)
- **Binary Protocol**: GPS may still be outputting binary instead of NMEA - watch for errors

## If Still Not Working

The GPS might be in binary mode. Try:
```bash
python3 configure_gps.py /dev/ttyTHS1 115200 115200
```

Or use Waveshare QGNSS software (Windows) to configure it to NMEA mode.

## Files Created for Troubleshooting

- `test_gps_standalone.py` - Test GPS without ROS
- `test_gps_comms.py` - Test if module is responding
- `configure_gps.py` - Try to configure GPS to NMEA mode
- `gps_troubleshooting.md` - Full troubleshooting guide
- `reset_gps.py` - Attempt factory reset

