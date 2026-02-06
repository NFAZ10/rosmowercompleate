# GPS/RTK ROS2 Package

ROS2 driver for GPS/RTK modules connected via UART on the 40-pin GPIO header.

## Features

- NMEA protocol parsing (GGA, RMC, VTG messages)
- Publishes `sensor_msgs/NavSatFix` for position
- Publishes `geometry_msgs/TwistStamped` for velocity
- Publishes raw NMEA sentences
- RTK support (Fixed and Float solutions)
- Configurable serial port and baud rate

## Hardware Setup

### GPIO UART Connection (40-pin Header)

The GPS module should be connected to the UART pins on the 40-pin GPIO header:

- **Pin 8 (GPIO 14)** - TX (Transmit) → Connect to GPS RX
- **Pin 10 (GPIO 15)** - RX (Receive) → Connect to GPS TX
- **Pin 6 or Pin 9** - GND (Ground) → Connect to GPS GND
- **Pin 2 or Pin 4** - 5V or 3.3V Power → Connect to GPS VCC (check your GPS module voltage requirements!)

### Enable UART on Raspberry Pi

1. Edit `/boot/config.txt` or `/boot/firmware/config.txt`:
   ```bash
   sudo nano /boot/config.txt
   ```

2. Add or uncomment these lines:
   ```
   enable_uart=1
   dtoverlay=disable-bt
   ```

3. Disable the serial console (if enabled):
   ```bash
   sudo raspi-config
   # Navigate to: Interface Options → Serial Port
   # Would you like a login shell accessible over serial? → No
   # Would you like the serial port hardware to be enabled? → Yes
   ```

4. Reboot:
   ```bash
   sudo reboot
   ```

5. Verify the UART device exists:
   ```bash
   ls -l /dev/ttyAMA0
   ```

### Add User to dialout Group

To access the serial port without root privileges:
```bash
sudo usermod -a -G dialout $USER
```
Log out and log back in for the change to take effect.

## Installation

1. Install dependencies:
   ```bash
   pip3 install pyserial pynmea2
   ```

2. Build the package:
   ```bash
   cd /mnt/nova_ssd/rosmowercompleate
   colcon build --packages-select gps_rtk
   source install/setup.bash
   ```

## Usage

### Launch with default parameters:
```bash
ros2 launch gps_rtk gps.launch.py
```

### Launch with custom serial port:
```bash
ros2 launch gps_rtk gps.launch.py serial_port:=/dev/ttyUSB0
```

### Launch with custom baud rate:
```bash
ros2 launch gps_rtk gps.launch.py baud_rate:=115200
```

### Enable RTK mode:
```bash
ros2 launch gps_rtk gps.launch.py use_rtk:=true
```

### Run node directly:
```bash
ros2 run gps_rtk gps_node --ros-args -p serial_port:=/dev/ttyAMA0 -p baud_rate:=9600
```

## Published Topics

- `/gps/fix` (`sensor_msgs/NavSatFix`) - GPS position fix with latitude, longitude, altitude
- `/gps/velocity` (`geometry_msgs/TwistStamped`) - Ground velocity from GPS
- `/gps/nmea_sentence` (`std_msgs/String`) - Raw NMEA sentences

## Parameters

- `serial_port` (string, default: `/dev/ttyAMA0`) - Serial port device
- `baud_rate` (int, default: `9600`) - Serial baud rate
- `frame_id` (string, default: `gps`) - TF frame ID
- `publish_rate` (float, default: `10.0`) - Publishing rate in Hz
- `use_rtk` (bool, default: `false`) - Enable RTK mode logging

## Testing

### Monitor GPS fix:
```bash
ros2 topic echo /gps/fix
```

### Monitor raw NMEA:
```bash
ros2 topic echo /gps/nmea_sentence
```

### Check GPS status:
```bash
ros2 topic hz /gps/fix
```

### Test serial connection manually:
```bash
cat /dev/ttyAMA0
```
You should see NMEA sentences like:
```
$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47
$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A
```

## Common GPS Modules

- **NEO-6M/7M/8M** - Standard GPS (usually 9600 baud)
- **NEO-M8P/M8T** - RTK capable (9600 or 115200 baud)
- **ZED-F9P** - High-precision RTK (38400 or 115200 baud)
- **BN-880** - GPS with compass (9600 baud)

## Troubleshooting

1. **No data from GPS:**
   - Check wiring (TX/RX might be swapped)
   - Verify serial port exists: `ls -l /dev/ttyAMA0`
   - Check permissions: `sudo chmod 666 /dev/ttyAMA0`
   - Ensure GPS has clear view of sky (GPS needs satellite signal)

2. **Permission denied:**
   - Add user to dialout group: `sudo usermod -a -G dialout $USER`
   - Or run with sudo (not recommended)

3. **Wrong baud rate:**
   - Try common rates: 4800, 9600, 19200, 38400, 115200
   - Check GPS module documentation

4. **UART not working:**
   - Verify UART is enabled in `/boot/config.txt`
   - Check Bluetooth isn't using the UART
   - Reboot after config changes

## RTK Setup

For RTK (Real-Time Kinematic) positioning:

1. You need an RTK-capable GPS module (e.g., ZED-F9P, M8P)
2. Set up a base station or use NTRIP service
3. Configure your GPS module to receive RTK corrections
4. Launch with `use_rtk:=true`

RTK can provide centimeter-level accuracy!

## License

Apache-2.0
