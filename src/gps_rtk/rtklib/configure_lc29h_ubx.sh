#!/bin/bash
# Configure LC29HDA to output UBX format for RTKLIB

DEVICE="/dev/ttyTHS1"
BAUD="115200"

echo "Configuring LC29HDA to UBX format..."

# Stop gpsd if running
sudo killall gpsd 2>/dev/null

# Send configuration commands via stty
stty -F $DEVICE $BAUD raw -echo

# Disable NMEA messages
echo -e "\$PAIR062,0,0*3F\r\n" > $DEVICE
sleep 0.2

# Enable UBX protocol output
echo -e "\$PAIR062,1,1*3E\r\n" > $DEVICE
sleep 0.2

# Save configuration to flash
echo -e "\$PAIR513*3D\r\n" > $DEVICE
sleep 0.5

echo "Configuration sent. Verify output format:"
timeout 3 cat $DEVICE | xxd | head -20

echo ""
echo "If you see binary data (not readable NMEA), UBX is enabled."
echo "To revert to NMEA, run: configure_lc29h_nmea.sh"
