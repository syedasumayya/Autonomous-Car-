"""
imu_test.py
-----------
Basic sanity check for the MPU6050 IMU on the I2C bus at address 0x68.
Prints raw accelerometer (m/s^2) and gyroscope (deg/s) values.

Wiring:
    MPU6050 VCC -> Pi 3.3 V (pin 1)     -- NOT 5 V
    MPU6050 GND -> Pi GND (common)
    MPU6050 SDA -> Pi GPIO 2 (pin 3)
    MPU6050 SCL -> Pi GPIO 3 (pin 5)

I2C must be enabled first (raspi-config -> Interface Options -> I2C).
Verify the sensor appears at address 0x68 with:

    sudo i2cdetect -y 1
"""

from mpu6050 import mpu6050
import time

mpu = mpu6050(0x68)

print("MPU6050 test. Ctrl+C to stop.")
try:
    while True:
        accel = mpu.get_accel_data()
        gyro = mpu.get_gyro_data()
        print(
            f"Ax:{accel['x']:6.2f} Ay:{accel['y']:6.2f} Az:{accel['z']:6.2f} | "
            f"Gx:{gyro['x']:7.2f} Gy:{gyro['y']:7.2f} Gz:{gyro['z']:7.2f}"
        )
        time.sleep(0.2)
except KeyboardInterrupt:
    print("done")
