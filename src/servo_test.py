"""
servo_test.py
-------------
Tests the MG90S steering servo and helps find the centre and the
left/right steering limits.

Wiring:
  Servo signal (orange) -> Pi GPIO 18 (physical pin 12)
  Servo power  (red)    -> 5 V supply (from the L298N's +5V output)
  Servo ground (brown)  -> common ground (servo GND + L298N GND + Pi GND)

Notes:
  - All grounds must be tied together, or the servo will not move.
  - The MG90S uses 500 - 2500 us pulse widths, wider than the SG90's
    1000 - 2000 us. The pulse_width settings below reflect that.
  - The MG90S has metal gears and tolerates stall better than the SG90,
    but stopping at the mechanical limits is still recommended.

How to use:
  Type an angle and press Enter. Type 'q' to quit.
  1. Find the centre: the angle where the wheels point straight.
  2. Find the limits: increase in small steps; note the angle at which
     the servo reaches its mechanical stop.

Findings on this vehicle:
  Straight :  10
  Full left:  90
  Full right: -23
  These asymmetric values are used by lane.py, corner_test.py, and
  combined.py so the steering command respects the actual travel range.

Status: tested and working.
"""

from gpiozero import AngularServo
from gpiozero.pins.pigpio import PiGPIOFactory

factory = PiGPIOFactory()

servo = AngularServo(
    18,
    min_angle=-90, max_angle=90,
    min_pulse_width=0.0005,   # MG90S: ~500 us
    max_pulse_width=0.0025,   # MG90S: ~2500 us
    pin_factory=factory,
)

print("Type an angle (-90 to 90). 'q' to quit.")

while True:
    x = input("angle: ")
    if x == "q":
        break
    try:
        servo.angle = float(x)
    except ValueError:
        print("Please type a number.")

servo.detach()
