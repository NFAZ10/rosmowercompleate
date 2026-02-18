#!/bin/bash
# Reset RPLiDAR A1 by power cycling USB port or sending reset commands

set -e

DEVICE="${1:-/dev/ttyUSB2}"

echo "Resetting RPLiDAR on $DEVICE..."

# Kill any existing processes using the device
if lsof "$DEVICE" >/dev/null 2>&1; then
    echo "Killing processes using $DEVICE..."
    PIDS=$(lsof -t "$DEVICE" 2>/dev/null || true)
    if [ -n "$PIDS" ]; then
        for PID in $PIDS; do
            echo "Killing process $PID"
            kill -9 "$PID" 2>/dev/null || true
        done
    fi
    sleep 1
fi

# Reset serial port settings
echo "Resetting serial port configuration..."
stty -F "$DEVICE" 115200 cs8 -cstopb -parenb raw -echo || echo "Warning: Could not configure $DEVICE"

# Send stop scan command (0xA5 0x25)
# This tells the LiDAR to stop scanning if it's stuck in scan mode
echo "Sending stop command to LiDAR..."
printf '\x25' > "$DEVICE" 2>/dev/null || echo "Warning: Could not send stop command"

sleep 0.5

# Send reset command (0xA5 0x40)
echo "Sending reset command to LiDAR..."
printf '\x40' > "$DEVICE" 2>/dev/null || echo "Warning: Could not send reset command"

sleep 1

echo "LiDAR reset complete. Ready to start."
