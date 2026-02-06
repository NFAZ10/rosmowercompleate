#!/usr/bin/env python3
"""
Configure Waveshare LC29H GPS module to output NMEA sentences at 115200 baud
Sends PAIR commands to enable NMEA output and configure baud rate
"""

import serial
import time
import sys

def calculate_nmea_checksum(sentence):
    """Calculate NMEA checksum (XOR of all bytes between $ and *)."""
    checksum = 0
    # Remove $ and everything after *
    sentence = sentence.strip('$').split('*')[0]
    for char in sentence:
        checksum ^= ord(char)
    return f"{checksum:02X}"

def send_command(ser, command, wait=0.5):
    """Send NMEA command and wait for response."""
    print(f"  Sending: {command.strip()}")
    ser.write(command.encode('ascii'))
    ser.flush()
    time.sleep(wait)
    
    # Read response
    response = ""
    if ser.in_waiting > 0:
        try:
            response = ser.read(ser.in_waiting).decode('ascii', errors='ignore')
            if response.strip():
                print(f"  Response: {response.strip()}")
        except:
            pass
    return response

def configure_gps(port='/dev/ttyACM0', current_baud=9600, target_baud=115200):
    """Configure GPS module for NMEA output."""
    
    print(f"\n{'='*70}")
    print(f"LC29H GPS Configuration Tool")
    print(f"{'='*70}")
    print(f"Port:         {port}")
    print(f"Current Baud: {current_baud}")
    print(f"Target Baud:  {target_baud}")
    print(f"{'='*70}\n")
    
    try:
        # Open at current baud rate
        print(f"[1] Connecting at {current_baud} baud...")
        ser = serial.Serial(
            port=port,
            baudrate=current_baud,
            timeout=2,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        print(f"    ✓ Connected\n")
        
        # Clear buffer
        time.sleep(0.5)
        ser.reset_input_buffer()
        
        # Commands to configure LC29H for NMEA output
        print(f"[2] Configuring NMEA output...")
        
        # Enable NMEA protocol output
        # PAIR062 enables message output
        # Format: $PAIR062,<msg_id>,<rate>*checksum
        # msg_id: 0=GGA, 1=GLL, 2=GSA, 3=GSV, 4=RMC, 5=VTG, 6=ZDA
        
        commands = [
            "$PAIR062,0,1*3F\r\n",  # Enable GGA at 1Hz
            "$PAIR062,4,1*3B\r\n",  # Enable RMC at 1Hz  
            "$PAIR062,5,1*3A\r\n",  # Enable VTG at 1Hz
            "$PAIR062,2,1*3D\r\n",  # Enable GSA at 1Hz
            "$PAIR062,3,1*3C\r\n",  # Enable GSV at 1Hz
        ]
        
        for cmd in commands:
            send_command(ser, cmd, wait=0.3)
        
        print()
        
        # Change baud rate if needed
        if current_baud != target_baud:
            print(f"[3] Changing baud rate to {target_baud}...")
            
            # PAIR513 sets baud rate
            # Baud rate codes: 0=4800, 1=9600, 2=19200, 3=38400, 4=57600, 5=115200
            baud_codes = {
                4800: 0,
                9600: 1,
                19200: 2,
                38400: 3,
                57600: 4,
                115200: 5
            }
            
            if target_baud in baud_codes:
                code = baud_codes[target_baud]
                cmd = f"$PAIR513,{code}*"
                checksum = calculate_nmea_checksum(cmd)
                cmd = f"{cmd}{checksum}\r\n"
                
                send_command(ser, cmd, wait=1.0)
                
                # Close and reopen at new baud rate
                ser.close()
                time.sleep(1)
                
                print(f"    Reopening at {target_baud} baud...")
                ser = serial.Serial(
                    port=port,
                    baudrate=target_baud,
                    timeout=2,
                    bytesize=serial.EIGHTBITS,
                    parity=serial.PARITY_NONE,
                    stopbits=serial.STOPBITS_ONE
                )
                print(f"    ✓ Reconnected at {target_baud}\n")
        else:
            print(f"[3] Already at {target_baud} baud, skipping...\n")
        
        # Verify NMEA output
        print(f"[4] Verifying NMEA output (10 seconds)...")
        start = time.time()
        nmea_count = 0
        
        while time.time() - start < 10:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('ascii', errors='ignore').strip()
                    if line.startswith('$'):
                        nmea_count += 1
                        if nmea_count <= 5:
                            print(f"    {line}")
                except:
                    pass
            time.sleep(0.01)
        
        ser.close()
        
        print(f"\n{'='*70}")
        if nmea_count > 0:
            print(f"✓ SUCCESS! Received {nmea_count} NMEA sentences")
            print(f"{'='*70}\n")
            print(f"GPS is now configured:")
            print(f"  • Port: {port}")
            print(f"  • Baud: {target_baud}")
            print(f"  • Protocol: NMEA 0183")
            print(f"\nUpdate your ROS config:")
            print(f"  serial_port: '{port}'")
            print(f"  baud_rate: {target_baud}")
            return True
        else:
            print(f"✗ FAILED - No NMEA sentences received")
            print(f"{'='*70}\n")
            print(f"The module may still be in binary mode.")
            print(f"Try using Waveshare QGNSS software to configure it.")
            return False
            
    except serial.SerialException as e:
        print(f"\n✗ Serial error: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    # Parse arguments
    if len(sys.argv) < 2:
        print("Usage: python3 configure_gps.py <port> [current_baud] [target_baud]")
        print("\nExamples:")
        print("  python3 configure_gps.py /dev/ttyACM0")
        print("  python3 configure_gps.py /dev/ttyACM0 9600 115200")
        print("\nDefault: current_baud=9600, target_baud=115200")
        sys.exit(1)
    
    port = sys.argv[1]
    current_baud = int(sys.argv[2]) if len(sys.argv) > 2 else 9600
    target_baud = int(sys.argv[3]) if len(sys.argv) > 3 else 115200
    
    success = configure_gps(port, current_baud, target_baud)
    sys.exit(0 if success else 1)
