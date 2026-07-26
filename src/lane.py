"""
lane.py
-------
Keeps the vehicle centred between two walls using the left and right
ultrasonic sensors. If the front sensor sees a wall coming up close,
the vehicle backs up instead of stopping; if the back sensor also sees
a wall, the vehicle judges itself stuck and simply stops.

Steering convention on this vehicle (asymmetric):
    servo.angle =  STRAIGHT_ANGLE  (10)  -> wheels straight
    servo.angle =  LEFT_ANGLE      (90)  -> full left
    servo.angle =  RIGHT_ANGLE    (-23)  -> full right

Positive steer values turn LEFT, negative values turn RIGHT.
Because the vehicle's right-side steering travel is limited to about
33 deg (versus 80 deg on the left), the steer() helper caps each side
independently rather than clipping to a single symmetric range.

Control law:
    error = left_distance - right_distance    (both walls visible)
    error = left  - TARGET_SIDE               (only left wall visible)
    error = TARGET_SIDE - right               (only right wall visible)
    steering = Kp * error

The pigpio pin factory must be running for accurate sensor timing:

    sudo systemctl start pigpiod
"""

from gpiozero import DistanceSensor, Motor, AngularServo, Device
from gpiozero.pins.pigpio import PiGPIOFactory
import time
import warnings

warnings.filterwarnings("ignore")

Device.pin_factory = PiGPIOFactory()

# ----- SENSORS -----
left  = DistanceSensor(echo=6,  trigger=5,  max_distance=2.0)
right = DistanceSensor(echo=19, trigger=13, max_distance=2.0)
front = DistanceSensor(echo=16, trigger=26, max_distance=2.0)
back  = DistanceSensor(echo=8,  trigger=22, max_distance=2.0)

# ----- STEERING GEOMETRY -----
STRAIGHT_ANGLE = 10        # servo angle when wheels are straight
LEFT_ANGLE     = 90        # servo angle at full left
RIGHT_ANGLE    = -23       # servo angle at full right
MAX_LEFT_OFFSET  = LEFT_ANGLE - STRAIGHT_ANGLE     # +80
MAX_RIGHT_OFFSET = STRAIGHT_ANGLE - RIGHT_ANGLE    # +33

# ----- DRIVING PARAMETERS -----
SPEED         = 0.30
REVERSE_SPEED = 0.25
Kp            = 2.5

TARGET_SIDE   = 25         # cm to hold from a single visible wall
WALL_MAX      = 80         # a reading beyond this is treated as "no wall"
FRONT_LIMIT   = 25         # start reversing when front < this (cm)
BACK_LIMIT    = 15         # stop reversing if back < this (cm)

# ----- ACTUATORS -----
motor = Motor(forward=23, backward=24, enable=12, pwm=True)
servo = AngularServo(
    18,
    min_angle=-90, max_angle=90,
    min_pulse_width=0.0005, max_pulse_width=0.0025,
)


def steer(direction):
    """direction: + = LEFT, - = RIGHT. Asymmetric limits are applied."""
    if direction >= 0:
        d = min(direction, MAX_LEFT_OFFSET)
    else:
        d = max(direction, -MAX_RIGHT_OFFSET)
    servo.angle = STRAIGHT_ANGLE + d


def read(sensor):
    try:
        return sensor.distance * 100
    except Exception:
        return 200


print("Lane follow with smart reverse. Ctrl+C to stop.")
time.sleep(2)

try:
    while True:
        l = read(left)
        r = read(right)
        f = read(front)
        b = read(back)

        # ---- Front is blocked ----
        if f < FRONT_LIMIT:
            if b < BACK_LIMIT:
                # Boxed in from both sides. Give up rather than grind.
                motor.stop()
                steer(0)
                print(f"STUCK  F:{f:.0f} B:{b:.0f}")
                time.sleep(0.1)
                continue

            # Reverse while turning the nose toward whichever side has
            # more free space. This nudges the vehicle out of a corner.
            if l < r:
                steer(+MAX_LEFT_OFFSET)
                print(f"REV+L  F:{f:.0f} B:{b:.0f} L:{l:.0f} R:{r:.0f}")
            else:
                steer(-MAX_RIGHT_OFFSET)
                print(f"REV+R  F:{f:.0f} B:{b:.0f} L:{l:.0f} R:{r:.0f}")

            motor.backward(REVERSE_SPEED)
            time.sleep(0.1)
            continue

        # ---- Normal driving: proportional lane hold ----
        motor.forward(SPEED)

        l_seen = l < WALL_MAX
        r_seen = r < WALL_MAX

        if l_seen and r_seen:
            error = l - r
        elif l_seen:
            error = l - TARGET_SIDE
        elif r_seen:
            error = TARGET_SIDE - r
        else:
            error = 0

        steering = Kp * error
        steer(steering)
        print(f"LANE   L:{l:.0f} R:{r:.0f} F:{f:.0f} err:{error:.0f} st:{steering:.0f}")
        time.sleep(0.05)
finally:
    motor.stop()
    servo.detach()
    print("done")
