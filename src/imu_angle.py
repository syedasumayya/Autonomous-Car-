"""
imu_angle.py
------------
Tracks the vehicle's yaw angle (heading) using the MPU6050 gyroscope's
Z axis. Steps:

1. Sample Gz for ~1 second while the vehicle is still to estimate the
   sensor bias.
2. In the main loop, subtract the bias from every reading and integrate
   over time:  angle += (Gz - bias) * dt

Sign convention on this build:
    Left  turn -> +90 deg
    Right turn -> -90 deg

Gyro-based integration drifts slowly over long periods, but a corner
turn only lasts a few seconds, so drift is not a practical issue for a
90 deg turn.
"""

from mpu6050 import mpu6050
import time

mpu = mpu6050(0x68)

# ----- CALIBRATION -----
print("Calibrating... keep the vehicle still for ~2 s...")
time.sleep(1)

N = 100
bias_sum = 0.0
for _ in range(N):
    bias_sum += mpu.get_gyro_data()["z"]
    time.sleep(0.01)
BIAS = bias_sum / N
print(f"Bias Gz = {BIAS:+.3f} deg/s")

# ----- INTEGRATION LOOP -----
angle = 0.0
last_t = time.time()

print("\nRotate the vehicle. Ctrl+C to stop.\n")

try:
    while True:
        now = time.time()
        dt = now - last_t
        last_t = now

        gz = mpu.get_gyro_data()["z"] - BIAS
        angle += gz * dt

        print(f"Angle: {angle:+7.1f} deg   (Gz: {gz:+6.1f} deg/s)", end="\r")
        time.sleep(0.02)
except KeyboardInterrupt:
    print(f"\nFinal angle: {angle:.1f} deg")
