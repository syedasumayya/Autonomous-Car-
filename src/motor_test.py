"""
motor_test.py
-------------
Tests the DC drive motor through the L298N motor driver.

Wiring:
  Pi GPIO 12 -> L298N ENA  (speed / PWM)   -- remove the ENA jumper
  Pi GPIO 23 -> L298N IN1  (direction)
  Pi GPIO 24 -> L298N IN2  (direction)
  Battery    -> L298N +12V and GND
  L298N GND  -> Pi GND     (common ground)
  Motor      -> L298N OUT1 / OUT2

Safety: keep the wheels off the ground while testing.
Status: tested and working (forward / reverse / stop).
"""

from gpiozero import Motor
import time

motor = Motor(forward=23, backward=24, enable=12, pwm=True)

print("Forward 2 s...")
motor.forward(0.6)
time.sleep(2)
motor.stop()
time.sleep(1)

print("Reverse 2 s...")
motor.backward(0.6)
time.sleep(2)
motor.stop()

print("Done.")
