#!/usr/bin/env python3
"""
Test if LC29H GPS module is communicating at all
Sends commands and checks for ANY response from the module
"""

import serial
import time
import sys

def test_module_communication(port='/dev/ttyAMA0', baudrate=115200):
    """Test if the GPS module responds to commands."""
    
    print(f"\n{'='*70}")
    print(f"LC29H Module Communication Test")
    print(f"{'='*70}")
    print(f"Port:     {port}")
    print(f"Baudrate: {baudrate}")
    print(f"{'='*70}\n")
    
    # NMEA commands to try
    # These are standard NMEA configuration queries
    commands = [
        # Query firmware version
        b'$PAIR001*3D\r\n',
        # Query current configuration  
        b'$PAIR050*38\r\n',
        # Request GGA message
        b'$PAIR062,1,0*3E\r\n',
        # Poll for position
        b'$PAIR513*3D\r\n',
    ]
    
    try:
        print(f"[1] Opening serial port {port}...")
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=1,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        print(f"    ✓ Port opened\n")
        
        # First, listen for any spontaneous output
        print(f"[2] Listening for spontaneous output (5 seconds)...")
        start = time.time()
        got_data = False
        while time.time() - start < 5:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                print(f"    ✓ Received {len(data)} bytes:")
                try:
                    print(f"      {data.decode('ascii', errors='ignore')}")
                except:
                    print(f"      (binary): {data.hex()}")
                got_data = True
            time.sleep(0.1)
        
        if not got_data:
            print(f"    ✗ No spontaneous output\n")
        else:
            print(f"    ✓ Module IS transmitting!\n")
            ser.close()
            return True
        
        # Try sending commands
        print(f"[3] Sending commands to module...")
        for i, cmd in enumerate(commands, 1):
            print(f"\n    Command {i}: {cmd.decode('ascii', errors='ignore').strip()}")
            
            # Clear any existing data
            ser.reset_input_buffer()
            
            # Send command
            ser.write(cmd)
            ser.flush()
            print(f"    → Sent, waiting for response...")
            
            # Wait for response
            time.sleep(0.5)
            
            if ser.in_waiting > 0:
                response = ser.read(ser.in_waiting)
                print(f"    ✓ Got response ({len(response)} bytes):")
                try:
                    print(f"      {response.decode('ascii', errors='ignore')}")
                except:
                    print(f"      (binary): {response.hex()}")
                got_data = True
            else:
                print(f"    ✗ No response")
        
        ser.close()
        
        print(f"\n{'='*70}")
        print(f"RESULT: {'Module IS communicating!' if got_data else 'Module NOT responding'}")
        print(f"{'='*70}\n")
        
        if not got_data:
            print("Possible causes:")
            print("  • Module not powered")
            print("  • Wrong serial port")
            print("  • Wrong baud rate") 
            print("  • Hardware failure")
            print("  • UART not enabled on Raspberry Pi")
            print("\nTry:")
            print("  1. Check power LEDs on the HAT")
            print("  2. Test other baud rates: 9600, 38400, 57600")
            print("  3. Test other ports: /dev/ttyUSB0, /dev/ttyACM0")
            print("  4. Check jumper position")
        
        return got_data
        
    except serial.SerialException as e:
        print(f"\n✗ Serial port error: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_all_bauds(port='/dev/ttyAMA0'):
    """Test all common baud rates."""
    print(f"\n{'='*70}")
    print(f"Testing all baud rates on {port}")
    print(f"{'='*70}\n")
    
    bauds = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600]
    
    for baud in bauds:
        print(f"\nTesting {baud} baud...")
        try:
            ser = serial.Serial(port, baud, timeout=0.5)
            time.sleep(0.5)
            
            if ser.in_waiting > 0:
                data = ser.read(min(100, ser.in_waiting))
                print(f"  ✓ GOT DATA at {baud}:")
                print(f"    {data.decode('ascii', errors='ignore')[:100]}")
                ser.close()
                return baud
            else:
                print(f"  ✗ No data")
                
            ser.close()
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
    
    return None


if __name__ == '__main__':
    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyAMA0'
    
    if len(sys.argv) > 2 and sys.argv[2] == '--all-bauds':
        found_baud = test_all_bauds(port)
        if found_baud:
            print(f"\n✓ Module found at {found_baud} baud!")
        else:
            print(f"\n✗ Module not responding at any baud rate")
    else:
        baud = int(sys.argv[2]) if len(sys.argv) > 2 else 115200
        success = test_module_communication(port, baud)
        sys.exit(0 if success else 1)
