# GPS/RTK Troubleshooting Guide - Waveshare LC29H(XX)

## Current Status
❌ **GPS Module NOT Detected** - No NMEA data on any serial port

## Diagnostic Results
- ✅ User in `dialout` group 
- ✅ Serial ports exist (`/dev/ttyAMA0`, `/dev/ttyUSB0`)
- ✅ No processes blocking the ports
- ❌ **NO DATA from GPS module**

---

## Hardware Checklist (Check These First!)

### 1. Antenna Connection ⭐ CRITICAL
- [ ] Is the L1/L5 dual-frequency antenna connected to the IPEX connector?
- [ ] Is the antenna positioned with clear view of the sky? (Not indoors/blocked)
- [ ] Is the antenna away from metal objects and interference sources?

**The GPS WILL NOT WORK without proper antenna placement!**

### 2. Power & LED Indicators
- [ ] Is the HAT receiving 5V power?
- [ ] Are any LEDs on the board lit?
  - **PPS LED**: Blinks when GPS has a fix
  - **RXD/TXD LEDs**: Blink when data is transmitted
- [ ] Is the HAT properly seated on the 40-pin GPIO header?

### 3. Jumper Configuration
The LC29H has a yellow jumper that selects communication mode:
- [ ] **Position B** (default): Uses GPIO UART → `/dev/ttyAMA0` (Pi 5) or `/dev/ttyS0` (Pi 4)
- [ ] **Position A**: Uses USB → `/dev/ttyUSB0`

**Current testing shows no data on either mode!**

### 4. Battery for Hot Start (Optional but helpful)
- [ ] Is ML1220 rechargeable battery installed in the onboard battery holder?
  - This preserves ephemeris data for faster GPS acquisition after power cycles

---

## Software Configuration Issues

### Current ROS Node Configuration
File: `src/gps_rtk/gps_rtk/gps_node.py`

**PROBLEM FOUND:**
```python
self.declare_parameter('baud_rate', 9600)  # ❌ WRONG!
```

**LC29H Default Baud Rate: 115200** (per Waveshare documentation)

### Fix for ROS Node:
Edit `src/gps_rtk/config/gps_params.yaml` or change default in node:
```yaml
gps_node:
  ros__parameters:
    serial_port: '/dev/ttyAMA0'  # or /dev/ttyS0 for Pi 4
    baud_rate: 115200            # ← Must be 115200, not 9600!
    frame_id: 'gps'
    publish_rate: 10.0
    use_rtk: false
```

---

## Testing Procedures

### Step 1: Verify Hardware First
Before ANY software testing:
1. **Connect antenna** to IPEX socket
2. **Place antenna outside** with clear sky view
3. **Power on and wait 26 seconds** (cold start acquisition time)
4. **Look for PPS LED blinking** (indicates GPS fix)

### Step 2: Test with Standalone Script
```bash
# Auto-detect GPS
python3 test_gps_standalone.py --auto

# Or specify port/baud explicitly:
python3 test_gps_standalone.py /dev/ttyAMA0 115200

# For USB mode (jumper on A):
python3 test_gps_standalone.py /dev/ttyUSB0 115200
```

### Step 3: If Still No Data - Try Serial Loopback Test
```bash
# This tests if the serial port hardware works at all
# Short pins 8 (TXD) and 10 (RXD) on the GPIO header with a jumper wire

# Terminal 1 - Listen:
cat /dev/ttyAMA0

# Terminal 2 - Send:
echo "TEST" > /dev/ttyAMA0

# You should see "TEST" in Terminal 1
# If not, there's a hardware/driver issue with UART
```

### Step 4: Check GPIO UART is Enabled
For Raspberry Pi 5:
```bash
# Check if UART is enabled in config
grep -i uart /boot/firmware/config.txt

# Should contain (add if missing):
# enable_uart=1
# dtoverlay=uart0
```

For Raspberry Pi 4:
```bash
grep -i uart /boot/config.txt
# Should have: enable_uart=1
```

After adding, reboot:
```bash
sudo reboot
```

---

## Common Issues & Solutions

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| No data on any port | Antenna not connected/positioned | Connect antenna, place outdoors |
| No LEDs lit | No power to module | Check 5V power, GPIO seating |
| Data on ttyUSB0 but not ttyAMA0 | Jumper in wrong position | Move jumper to position B |
| Intermittent data | Poor antenna placement | Move antenna to clear sky view |
| "No fix" in NMEA | Weak signal / indoors | Move antenna outdoors, wait 26s |
| Permission denied | User not in dialout group | `sudo usermod -a -G dialout $USER` + logout |

---

## Expected NMEA Output (When Working)

When GPS is working, you should see:
```
$GNGGA,010555.000,2232.4682,N,11404.6748,E,1,12,1.0,7.0,M,,,,*4F
$GNRMC,010555.000,A,2232.4682,N,11404.6748,E,0.00,125.29,230822,,,D*71
$GNVTG,125.29,T,,M,0.00,N,0.00,K,D*3E
$GNGSA,A,3,01,03,06,09,14,17,19,22,24,28,30,31,1.8,1.0,1.5,1*36
$GPGSV,3,1,12,01,45,045,39,03,15,210,25,06,51,165,43,09,15,094,28,1*63
...
```

Key indicators:
- **`$GN`**: Multi-GNSS (GPS + GLONASS + BeiDou + Galileo)
- **GGA field 6 = 0**: No fix
- **GGA field 6 = 1**: GPS fix (standard)
- **GGA field 6 = 4**: RTK Fixed (centimeter accuracy!)
- **GGA field 6 = 5**: RTK Float

---

## RTK Configuration (For Centimeter Accuracy)

**Only applies to LC29H(DA) and LC29H(BS) models!**

For RTK, you need:
1. **Base station** OR **NTRIP network** (e.g., rtk2go.com)
2. **Correction data** in RTCM 3.x format
3. Configure NTRIP client to send RTCM to GPS module

See: `NTRIP` section in Waveshare wiki for detailed setup

---

## Next Steps

1. ✅ **CHECK HARDWARE** (antenna, power, jumper, LEDs)
2. ✅ **Run test script** after hardware verification
3. ✅ **Fix baud rate** in ROS node configuration (9600 → 115200)
4. ✅ **Enable UART** in Pi config if needed
5. ✅ **Retest** with corrected configuration

---

## Useful Commands

```bash
# Monitor raw GPS data
python3 test_gps_standalone.py /dev/ttyAMA0 115200

# Check which process uses the port
lsof /dev/ttyAMA0

# Read raw serial data
stty -F /dev/ttyAMA0 115200 && cat /dev/ttyAMA0

# Monitor ROS GPS topics (after fixing)
ros2 topic echo /gps/fix
ros2 topic echo /gps/nmea_sentence

# Check GPS node status
ros2 node info /gps_node
```

---

## Reference Documentation
- Waveshare Wiki: https://www.waveshare.com/wiki/LC29H(XX)_GPS/RTK_HAT
- NMEA 0183 Protocol: Default GPS output format
- Default Baud: **115200 bps**
- Acquisition Time: Cold start 26s, Hot start 1s
- Fix Accuracy: 1m standard, 0.01m+1ppm with RTK

