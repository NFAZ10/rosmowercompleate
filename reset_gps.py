#!/usr/bin/env python3
import serial
import time

port = '/dev/ttyACM0'
baud = 9600

print("Attempting to reset GPS to NMEA mode...")
ser = serial.Serial(port, baud, timeout=1)
time.sleep(0.5)

# Try different reset/config commands for LC29H
commands = [
    # Factory reset
    b'$PAIR000*38\r\n',
    # Set to NMEA mode  
    b'$PAIR515,0*3B\r\n',
    # Set output to NMEA (not binary)
    b'$PAIR516,0*3A\r\n',
    # Cold restart
    b'$PAIR004*3E\r\n',
]

for cmd in commands:
    print(f"Sending: {cmd}")
    ser.write(cmd)
    time.sleep(1)

ser.close()
print("Commands sent. Waiting 5 seconds for restart...")
time.sleep(5)

# Check if NMEA now
print("\nChecking for NMEA output at 115200...")
ser = serial.Serial(port, 115200, timeout=2)
time.sleep(2)

for i in range(20):
    if ser.in_waiting > 0:
        line = ser.readline().decode('ascii', errors='ignore')
        if line.startswith('$'):
            print(f"✓ NMEA: {line.strip()}")
        else:
            print(f"Binary: {line[:50]}")
    time.sleep(0.5)

ser.close()
