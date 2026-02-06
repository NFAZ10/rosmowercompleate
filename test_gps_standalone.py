#!/usr/bin/env python3

"""
Standalone GPS/RTK test script - NO ROS REQUIRED
Tests Waveshare LC29H(XX) GPS/RTK HAT directly via serial

Usage:
  python3 test_gps_standalone.py [serial_port] [baud_rate]
  
Examples:
  python3 test_gps_standalone.py /dev/ttyAMA0 115200
  python3 test_gps_standalone.py /dev/ttyUSB0 115200
  python3 test_gps_standalone.py /dev/ttyS0 9600
"""

import serial
import sys
import time
from datetime import datetime

def test_gps(port='/dev/ttyTHS1', baudrate=115200, timeout=10):
    """
    Test GPS module by reading raw NMEA data.
    
    Args:
        port: Serial port (default: /dev/ttyAMA0 for Pi 5, /dev/ttyS0 for Pi 4)
        baudrate: Baud rate (default: 115200 - LC29H default)
        timeout: How long to read data in seconds
    """
    
    print(f"\n{'='*70}")
    print(f"GPS/RTK Standalone Test - Waveshare LC29H(XX)")
    print(f"{'='*70}")
    print(f"Port:      {port}")
    print(f"Baudrate:  {baudrate}")
    print(f"Timeout:   {timeout}s")
    print(f"{'='*70}\n")
    
    try:
        # Open serial connection
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Opening serial port...")
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=2.0,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE
        )
        
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ✓ Serial port opened successfully!")
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Waiting for GPS data...\n")
        
        start_time = time.time()
        line_count = 0
        gga_count = 0
        rmc_count = 0
        has_fix = False
        
        # Read data for specified timeout
        while (time.time() - start_time) < timeout:
            if ser.in_waiting > 0:
                try:
                    line = ser.readline().decode('ascii', errors='ignore').strip()
                    
                    if line.startswith('$'):
                        line_count += 1
                        timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]
                        
                        # Count message types
                        if 'GGA' in line:
                            gga_count += 1
                            print(f"[{timestamp}] {line}")
                            # Check for fix quality
                            parts = line.split(',')
                            if len(parts) > 6:
                                try:
                                    fix_quality = int(parts[6])
                                    if fix_quality > 0:
                                        has_fix = True
                                        fix_type = {
                                            0: "No fix",
                                            1: "GPS fix",
                                            2: "DGPS fix",
                                            4: "RTK Fixed",
                                            5: "RTK Float",
                                            6: "Estimated"
                                        }.get(fix_quality, f"Unknown ({fix_quality})")
                                        print(f"           >>> FIX QUALITY: {fix_type} <<<")
                                except (ValueError, IndexError):
                                    pass
                                    
                        elif 'RMC' in line:
                            rmc_count += 1
                            print(f"[{timestamp}] {line}")
                            # Check status
                            parts = line.split(',')
                            if len(parts) > 2:
                                status = parts[2]
                                if status == 'A':
                                    print(f"           >>> STATUS: Active (Valid) <<<")
                                elif status == 'V':
                                    print(f"           >>> STATUS: Void (Invalid) <<<")
                        else:
                            # Show other NMEA sentences
                            print(f"[{timestamp}] {line}")
                    
                except UnicodeDecodeError:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Warning: Decode error (non-ASCII data)")
                except Exception as e:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Error reading line: {e}")
            
            # Brief pause to prevent CPU spinning
            time.sleep(0.01)
        
        # Close connection
        ser.close()
        
        # Print summary
        print(f"\n{'='*70}")
        print(f"TEST SUMMARY ({timeout}s)")
        print(f"{'='*70}")
        print(f"Total NMEA sentences received: {line_count}")
        print(f"GGA messages (Position):       {gga_count}")
        print(f"RMC messages (Navigation):     {rmc_count}")
        print(f"GPS Fix detected:              {'YES ✓' if has_fix else 'NO ✗'}")
        print(f"{'='*70}\n")
        
        if line_count == 0:
            print("⚠ WARNING: No data received!")
            print("\nTroubleshooting steps:")
            print("  1. Check antenna is connected and has clear sky view")
            print("  2. Verify jumper position (B=GPIO UART, A=USB)")
            print("  3. Try different baud rates: 115200, 9600")
            print("  4. For Raspberry Pi 5, use /dev/ttyAMA0")
            print("  5. For Raspberry Pi 4, use /dev/ttyS0")
            print("  6. Check if serial port is in use: lsof /dev/ttyAMA0")
            print("  7. Verify user is in 'dialout' group: groups $USER")
            return False
        
        return line_count > 0
        
    except serial.SerialException as e:
        print(f"\n✗ SERIAL ERROR: {e}\n")
        print("Troubleshooting:")
        print(f"  • Is {port} the correct device?")
        print(f"  • Check available ports: ls -la /dev/tty*")
        print(f"  • Is port already in use? Run: lsof {port}")
        print(f"  • Are you in dialout group? Run: groups")
        print(f"  • If not, add yourself: sudo usermod -a -G dialout $USER")
        return False
    
    except KeyboardInterrupt:
        print("\n\n✓ Test interrupted by user")
        if 'ser' in locals() and ser.is_open:
            ser.close()
        return True
    
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def find_gps_auto():
    """Auto-detect GPS module on common ports and baud rates."""
    
    print("\n" + "="*70)
    print("AUTO-DETECTING GPS MODULE")
    print("="*70 + "\n")
    
    # Common ports for LC29H on Raspberry Pi
    ports = [
        '/dev/ttyAMA0',  # Pi 5 GPIO UART
        '/dev/ttyS0',    # Pi 4 GPIO UART
        '/dev/ttyUSB0',  # USB mode
    ]
    
    # LC29H supports 9600-3000000, but these are most common
    bauds = [115200, 9600, 38400, 57600]
    
    for port in ports:
        import os
        if not os.path.exists(port):
            print(f"⊘ {port} - not found")
            continue
            
        for baud in bauds:
            print(f"Testing {port} @ {baud} baud...", end=' ')
            try:
                ser = serial.Serial(port, baud, timeout=1)
                # Try to read for 2 seconds
                start = time.time()
                found_data = False
                while time.time() - start < 2:
                    if ser.in_waiting > 0:
                        line = ser.readline().decode('ascii', errors='ignore')
                        if line.startswith('$'):
                            found_data = True
                            break
                    time.sleep(0.1)
                
                ser.close()
                
                if found_data:
                    print("✓ FOUND GPS DATA!")
                    return port, baud
                else:
                    print("✗ no data")
                    
            except (serial.SerialException, PermissionError) as e:
                print(f"✗ {e}")
            except Exception as e:
                print(f"✗ error: {e}")
    
    print("\n✗ GPS module not found on any port/baud combination")
    return None, None


if __name__ == '__main__':
    # Parse command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--help', '-h']:
            print(__doc__)
            sys.exit(0)
        elif sys.argv[1] in ['--auto', '-a']:
            port, baud = find_gps_auto()
            if port and baud:
                print(f"\n✓ Running full test on {port} @ {baud}")
                test_gps(port, baud, timeout=30)
            sys.exit(0)
        
        port = sys.argv[1]
        baud = int(sys.argv[2]) if len(sys.argv) > 2 else 115200
        timeout_val = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    else:
        # Default values for LC29H on Pi 5
        port = '/dev/ttyAMA0'
        baud = 115200
        timeout_val = 10
        
        print("No arguments provided. Using defaults for LC29H on Raspberry Pi 5")
        print("For other configurations, use:")
        print("  python3 test_gps_standalone.py <port> <baud> [timeout]")
        print("Or auto-detect:")
        print("  python3 test_gps_standalone.py --auto")
        print()
    
    success = test_gps(port, baud, timeout_val)
    sys.exit(0 if success else 1)
