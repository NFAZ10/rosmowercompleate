#!/usr/bin/env python3
"""
ICM20948 9-axis IMU Hardware Driver
Supports accelerometer, gyroscope, and magnetometer
"""

import smbus2
import time
import struct
from typing import Tuple, Optional


class ICM20948:
    """ICM20948 9-axis IMU driver class"""
    
    # I2C Address
    ICM20948_ADDRESS = 0x68
    AK09916_ADDRESS = 0x0C  # Magnetometer I2C address (accessed via ICM20948)
    
    # ICM20948 Register Map
    WHO_AM_I = 0x00
    USER_CTRL = 0x03
    PWR_MGMT_1 = 0x06
    PWR_MGMT_2 = 0x07
    INT_PIN_CFG = 0x0F
    INT_ENABLE = 0x10
    INT_ENABLE_1 = 0x11
    INT_ENABLE_2 = 0x12
    INT_ENABLE_3 = 0x13
    
    ACCEL_XOUT_H = 0x2D
    GYRO_XOUT_H = 0x33
    TEMP_OUT_H = 0x39
    
    ACCEL_CONFIG = 0x14
    ACCEL_CONFIG_2 = 0x15
    GYRO_CONFIG_1 = 0x01
    GYRO_CONFIG_2 = 0x02
    
    # Bank selection
    REG_BANK_SEL = 0x7F
    
    # AK09916 Magnetometer registers
    MAG_WIA2 = 0x01
    MAG_ST1 = 0x10
    MAG_HXL = 0x11
    MAG_CNTL2 = 0x31
    MAG_CNTL3 = 0x32
    
    # Scales
    ACCEL_SCALE = {2: 16384.0, 4: 8192.0, 8: 4096.0, 16: 2048.0}
    GYRO_SCALE = {250: 131.0, 500: 65.5, 1000: 32.8, 2000: 16.4}
    MAG_SCALE = 4912.0 / 32760.0  # µT per LSB
    
    def __init__(self, i2c_bus: int = 1, address: int = ICM20948_ADDRESS):
        """Initialize ICM20948 sensor
        
        Args:
            i2c_bus: I2C bus number (default: 1)
            address: I2C address (default: 0x68)
        """
        self.bus = smbus2.SMBus(i2c_bus)
        self.address = address
        self.accel_range = 2  # ±2g
        self.gyro_range = 250  # ±250°/s
        
    def select_bank(self, bank: int):
        """Select register bank (0-3)"""
        self.bus.write_byte_data(self.address, self.REG_BANK_SEL, bank << 4)
        
    def initialize(self) -> bool:
        """Initialize the ICM20948 sensor
        
        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Select bank 0
            self.select_bank(0)
            
            # Check WHO_AM_I register
            who_am_i = self.bus.read_byte_data(self.address, self.WHO_AM_I)
            if who_am_i != 0xEA:
                print(f"ICM20948 WHO_AM_I check failed: 0x{who_am_i:02X} (expected 0xEA)")
                return False
            
            # Reset device
            self.bus.write_byte_data(self.address, self.PWR_MGMT_1, 0x80)
            time.sleep(0.1)
            
            # Auto-select clock source
            self.bus.write_byte_data(self.address, self.PWR_MGMT_1, 0x01)
            time.sleep(0.01)
            
            # Enable accelerometer and gyroscope
            self.bus.write_byte_data(self.address, self.PWR_MGMT_2, 0x00)
            time.sleep(0.01)
            
            # Configure accelerometer (±2g, DLPF)
            self.select_bank(2)
            self.bus.write_byte_data(self.address, self.ACCEL_CONFIG, 0x01)
            self.bus.write_byte_data(self.address, self.ACCEL_CONFIG_2, 0x09)
            
            # Configure gyroscope (±250°/s, DLPF)
            self.bus.write_byte_data(self.address, self.GYRO_CONFIG_1, 0x01)
            self.bus.write_byte_data(self.address, self.GYRO_CONFIG_2, 0x09)
            
            # Initialize magnetometer
            self.select_bank(0)
            self._init_magnetometer()
            
            return True
            
        except Exception as e:
            print(f"ICM20948 initialization error: {e}")
            return False
            
    def _init_magnetometer(self):
        """Initialize the AK09916 magnetometer"""
        try:
            # Enable I2C master mode
            self.select_bank(0)
            self.bus.write_byte_data(self.address, self.USER_CTRL, 0x20)
            time.sleep(0.01)
            
            # Configure I2C master
            self.select_bank(3)
            self.bus.write_byte_data(self.address, 0x01, 0x07)  # I2C_MST_CTRL
            time.sleep(0.01)
            
            # Reset magnetometer
            self._write_mag_register(self.MAG_CNTL3, 0x01)
            time.sleep(0.1)
            
            # Set continuous measurement mode (100Hz)
            self._write_mag_register(self.MAG_CNTL2, 0x08)
            time.sleep(0.01)
            
            self.select_bank(0)
            
        except Exception as e:
            print(f"Magnetometer initialization error: {e}")
            
    def _write_mag_register(self, reg: int, value: int):
        """Write to magnetometer register via I2C master"""
        self.select_bank(3)
        self.bus.write_byte_data(self.address, 0x06, self.AK09916_ADDRESS)  # I2C_SLV0_ADDR
        self.bus.write_byte_data(self.address, 0x07, reg)  # I2C_SLV0_REG
        self.bus.write_byte_data(self.address, 0x09, value)  # I2C_SLV0_DO
        self.bus.write_byte_data(self.address, 0x08, 0x81)  # I2C_SLV0_CTRL (enable, 1 byte)
        time.sleep(0.01)
        
    def _read_mag_registers(self, start_reg: int, length: int) -> bytes:
        """Read from magnetometer registers via I2C master"""
        self.select_bank(3)
        # Set up read operation
        self.bus.write_byte_data(self.address, 0x06, self.AK09916_ADDRESS | 0x80)  # I2C_SLV0_ADDR (read)
        self.bus.write_byte_data(self.address, 0x07, start_reg)  # I2C_SLV0_REG
        self.bus.write_byte_data(self.address, 0x08, 0x80 | length)  # I2C_SLV0_CTRL
        time.sleep(0.01)
        
        # Read from EXT_SLV_SENS_DATA registers
        self.select_bank(0)
        data = []
        for i in range(length):
            data.append(self.bus.read_byte_data(self.address, 0x3B + i))
        return bytes(data)
        
    def read_accel(self) -> Tuple[float, float, float]:
        """Read accelerometer data
        
        Returns:
            Tuple of (x, y, z) in m/s²
        """
        self.select_bank(0)
        data = self.bus.read_i2c_block_data(self.address, self.ACCEL_XOUT_H, 6)
        
        ax = struct.unpack('>h', bytes(data[0:2]))[0]
        ay = struct.unpack('>h', bytes(data[2:4]))[0]
        az = struct.unpack('>h', bytes(data[4:6]))[0]
        
        # Convert to m/s²
        scale = self.ACCEL_SCALE[self.accel_range]
        g = 9.80665
        return (ax / scale * g, ay / scale * g, az / scale * g)
        
    def read_gyro(self) -> Tuple[float, float, float]:
        """Read gyroscope data
        
        Returns:
            Tuple of (x, y, z) in rad/s
        """
        self.select_bank(0)
        data = self.bus.read_i2c_block_data(self.address, self.GYRO_XOUT_H, 6)
        
        gx = struct.unpack('>h', bytes(data[0:2]))[0]
        gy = struct.unpack('>h', bytes(data[2:4]))[0]
        gz = struct.unpack('>h', bytes(data[4:6]))[0]
        
        # Convert to rad/s
        scale = self.GYRO_SCALE[self.gyro_range]
        deg_to_rad = 3.14159265359 / 180.0
        return (gx / scale * deg_to_rad, gy / scale * deg_to_rad, gz / scale * deg_to_rad)
        
    def read_mag(self) -> Tuple[float, float, float]:
        """Read magnetometer data
        
        Returns:
            Tuple of (x, y, z) in Tesla
        """
        try:
            # Read magnetometer data
            data = self._read_mag_registers(self.MAG_HXL, 8)
            
            # Check status
            st1 = data[0]
            if not (st1 & 0x01):  # Data not ready
                return (0.0, 0.0, 0.0)
                
            mx = struct.unpack('<h', bytes(data[1:3]))[0]
            my = struct.unpack('<h', bytes(data[3:5]))[0]
            mz = struct.unpack('<h', bytes(data[5:7]))[0]
            
            # Convert to Tesla
            scale = self.MAG_SCALE * 1e-6  # µT to T
            return (mx * scale, my * scale, mz * scale)
            
        except Exception as e:
            print(f"Magnetometer read error: {e}")
            return (0.0, 0.0, 0.0)
            
    def read_temperature(self) -> float:
        """Read temperature
        
        Returns:
            Temperature in Celsius
        """
        self.select_bank(0)
        data = self.bus.read_i2c_block_data(self.address, self.TEMP_OUT_H, 2)
        temp_raw = struct.unpack('>h', bytes(data))[0]
        
        # Convert to Celsius
        return (temp_raw / 333.87) + 21.0
        
    def close(self):
        """Close I2C bus"""
        self.bus.close()
