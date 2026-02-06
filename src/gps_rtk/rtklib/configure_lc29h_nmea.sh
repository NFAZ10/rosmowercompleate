#!/bin/bash
# Revert LC29HDA back to NMEA format

DEVICE="/dev/ttyTHS1"
BAUD="115200"

echo "Reverting LC29HDA to NMEA format..."

# Stop gpsd if running
sudo killall gpsd 2>/dev/null

stty -F $DEVICE $BAUD raw -echo

# Enable NMEA messages
echo -e "\$PAIR062,0,1*3E\r\n" > $DEVICE
sleep 0.2

# Disable UBX protocol
echo -e "\$PAIR062,1,0*3F\r\n" > $DEVICE
sleep 0.2

# Save configuration to flash
echo -e "\$PAIR513*3D\r\n" > $DEVICE
sleep 0.5

echo "Configuration sent. You should see NMEA sentences:"
timeout 3 cat $DEVICE | head -10
