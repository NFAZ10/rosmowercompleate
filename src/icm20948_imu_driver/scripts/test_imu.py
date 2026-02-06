#!/usr/bin/env python3
"""
Test script for ICM20948 IMU hardware
Run this to verify the sensor is working before using ROS2
"""

import time
import sys

try:
    from icm20948_imu_driver.icm20948_driver import ICM20948
except ImportError:
    print("Warning: Could not import from package, trying local import")
    from icm20948_driver import ICM20948


def test_imu():
    """Test ICM20948 sensor"""
    print("=" * 60)
    print("ICM20948 IMU Test")
    print("=" * 60)
    
    # Initialize sensor
    print("\n1. Initializing sensor on I2C bus 1, address 0x68...")
    try:
        imu = ICM20948(i2c_bus=1, address=0x68)
    except Exception as e:
        print(f"ERROR: Failed to create ICM20948 instance: {e}")
        print("\nTroubleshooting:")
        print("- Check I2C is enabled")
        print("- Run: sudo i2cdetect -y 1")
        print("- Check permissions: sudo usermod -a -G i2c $USER")
        return False
    
    if not imu.initialize():
        print("ERROR: Failed to initialize ICM20948")
        print("\nTroubleshooting:")
        print("- Check wiring connections (SDA, SCL, VCC, GND)")
        print("- Verify I2C address with: sudo i2cdetect -y 1")
        print("- Expected address: 0x68")
        return False
    
    print("✓ Sensor initialized successfully!")
    
    # Read sensor data
    print("\n2. Reading sensor data (10 samples)...")
    print("-" * 60)
    print(f"{'Sample':<8} {'Accel (m/s²)':<30} {'Gyro (rad/s)':<30} {'Temp (°C)':<10}")
    print("-" * 60)
    
    try:
        for i in range(10):
            # Read accelerometer
            accel = imu.read_accel()
            
            # Read gyroscope
            gyro = imu.read_gyro()
            
            # Read temperature
            temp = imu.read_temperature()
            
            # Format output
            accel_str = f"({accel[0]:6.2f}, {accel[1]:6.2f}, {accel[2]:6.2f})"
            gyro_str = f"({gyro[0]:6.3f}, {gyro[1]:6.3f}, {gyro[2]:6.3f})"
            
            print(f"{i+1:<8} {accel_str:<30} {gyro_str:<30} {temp:6.2f}")
            
            time.sleep(0.1)
            
    except Exception as e:
        print(f"\nERROR: Failed to read sensor data: {e}")
        return False
    
    # Read magnetometer
    print("\n3. Reading magnetometer data (10 samples)...")
    print("-" * 60)
    print(f"{'Sample':<8} {'Magnetometer (Tesla)':<40}")
    print("-" * 60)
    
    try:
        for i in range(10):
            mag = imu.read_mag()
            mag_str = f"({mag[0]:10.6f}, {mag[1]:10.6f}, {mag[2]:10.6f})"
            print(f"{i+1:<8} {mag_str:<40}")
            time.sleep(0.1)
            
    except Exception as e:
        print(f"\nWARNING: Magnetometer read failed: {e}")
        print("This may be normal if magnetometer initialization had issues")
    
    # Close sensor
    imu.close()
    
    print("\n" + "=" * 60)
    print("✓ Test completed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Build the ROS2 package: colcon build --packages-select icm20948_imu_driver")
    print("2. Source the workspace: source install/setup.bash")
    print("3. Launch the node: ros2 launch icm20948_imu_driver icm20948.launch.py")
    print("4. View data: ros2 topic echo /imu/data_raw")
    
    return True


if __name__ == "__main__":
    success = test_imu()
    sys.exit(0 if success else 1)
