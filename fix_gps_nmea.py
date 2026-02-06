#!/usr/bin/env python3
"""
Force LC29H GPS into NMEA mode
Based on LC29H command set
"""
import serial
import time
import sys

port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyTHS1'
baud = int(sys.argv[2]) if len(sys.argv) > 2 else 115200

print(f"Configuring LC29H on {port} at {baud} baud")
print("=" * 60)

try:
    ser = serial.Serial(port, baud, timeout=1)
    time.sleep(0.5)
    
    # LC29H NMEA commands
    commands = [
        # Set output to NMEA (not binary/UBX)
        ('Set NMEA mode', b'$PAIR516,0*3A\r\n'),
        # Enable GGA
        ('Enable GGA', b'$PAIR062,0,1*3F\r\n'),
        # Enable RMC  
        ('Enable RMC', b'$PAIR062,4,1*3B\r\n'),
        # Enable GSA
        ('Enable GSA', b'$PAIR062,2,1*3D\r\n'),
        # Enable GSV
        ('Enable GSV', b'$PAIR062,3,1*3C\r\n'),
        # Enable VTG
        ('Enable VTG', b'$PAIR062,5,1*3A\r\n'),
        # Save configuration
        ('Save config', b'$PAIR513,0*28\r\n'),
    ]
    
    for desc, cmd in commands:
        print(f"\n{desc}: {cmd.decode().strip()}")
        ser.write(cmd)
        time.sleep(0.3)
        
        # Read response
        if ser.in_waiting > 0:
            response = ser.read(ser.in_waiting)
            # Check if NMEA response
            if b'$PAIR' in response:
                print(f"  ✓ Response: {response.decode('ascii', errors='ignore').strip()}")
            else:
                print(f"  Response: (binary, {len(response)} bytes)")
    
    ser.close()
    print("\n" + "=" * 60)
    print("Configuration sent. Waiting 3 seconds...")
    time.sleep(3)
    
    # Test NMEA output
    print("\nTesting NMEA output...")
    print("=" * 60)
    ser = serial.Serial(port, baud, timeout=2)
    time.sleep(1)
    
    nmea_count = 0
    for i in range(30):
        if ser.in_waiting > 0:
            try:
                line = ser.readline().decode('ascii', errors='ignore')
                if line.startswith('$'):
                    print(f"✓ {line.strip()}")
                    nmea_count += 1
                else:
                    print(f"? {repr(line[:60])}")
            except:
                pass
        time.sleep(0.3)
    
    ser.close()
    
    print("\n" + "=" * 60)
    if nmea_count > 0:
        print(f"✓ SUCCESS: Received {nmea_count} NMEA sentences")
        sys.exit(0)
    else:
        print("✗ FAILED: No NMEA sentences received")
        print("\nTroubleshooting:")
        print("1. Module may need power cycle")
        print("2. Try Waveshare QGNSS software (Windows)")
        print("3. Check antenna connection")
        sys.exit(1)
        
except Exception as e:
    print(f"\n✗ ERROR: {e}")
    sys.exit(1)
