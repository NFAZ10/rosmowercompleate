#!/bin/bash
echo "Testing all potential GPS ports on Jetson Orin..."
echo "================================================================"

for port in /dev/ttyUSB0 /dev/ttyTHS1 /dev/ttyTHS2 /dev/ttyAMA0; do
    if [ ! -e "$port" ]; then
        echo "⊘ $port - does not exist"
        continue
    fi
    
    echo ""
    echo "Testing $port at 115200 baud..."
    timeout 3 python3 -c "
import serial, time
try:
    ser = serial.Serial('$port', 115200, timeout=1)
    time.sleep(1)
    if ser.in_waiting > 0:
        data = ser.read(min(200, ser.in_waiting)).decode('ascii', errors='ignore')
        if '\$' in data:
            print('  ✓ NMEA DATA FOUND!')
            for line in data.split('\n'):
                if line.startswith('\$'):
                    print(f'    {line[:70]}')
        else:
            print('  ✗ Data but not NMEA')
    else:
        print('  ✗ No data')
    ser.close()
except Exception as e:
    print(f'  ✗ Error: {e}')
" 2>&1
done

echo ""
echo "================================================================"
