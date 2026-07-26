"""
avoid.py
--------
Pillar avoidance using the camera only. Combines pillar detection with
steering so the vehicle passes each coloured pillar on the correct side:

    Red pillar   -> keep RIGHT (steer negative)
    Green pillar -> keep LEFT  (steer positive)
    No pillar    -> hold straight

Steering values on this vehicle (from servo_test.py):
    Straight :  10
    Full left:  90
    Full right: -23

The motor line is commented out by default so the vehicle can be first
tested on a stand with the wheels off the ground. Uncomment the
`motor.forward(0.30)` line for a floor test.

To reduce servo jitter while the camera is active, the servo is only
commanded when the target angle actually changes, and the camera frame
rate is capped at 15 fps.
"""

from picamera2 import Picamera2
from gpiozero import Motor, AngularServo
from gpiozero.pins.pigpio import PiGPIOFactory
import cv2
import numpy as np

# ----- MOTOR / SERVO -----
factory = PiGPIOFactory()

STRAIGHT_ANGLE = 10
LEFT_ANGLE     = 90
RIGHT_ANGLE    = -23
MAX_LEFT_OFFSET  = LEFT_ANGLE - STRAIGHT_ANGLE
MAX_RIGHT_OFFSET = STRAIGHT_ANGLE - RIGHT_ANGLE

motor = Motor(forward=23, backward=24, enable=12, pwm=True)
servo = AngularServo(
    18,
    min_angle=-90, max_angle=90,
    min_pulse_width=0.0005, max_pulse_width=0.0025,
    pin_factory=factory,
)

last_angle = None


def steer(direction):
    """direction: + = LEFT, - = RIGHT. Only writes when the value changes."""
    global last_angle
    if direction >= 0:
        d = min(direction, MAX_LEFT_OFFSET)
    else:
        d = max(direction, -MAX_RIGHT_OFFSET)
    new_angle = STRAIGHT_ANGLE + d
    if last_angle is None or abs(new_angle - last_angle) > 1:
        servo.angle = new_angle
        last_angle = new_angle


# ----- VISION -----
W, H = 320, 240
MIN_AREA = 800   # pixels: how close a pillar must be before we react

GREEN_LO = np.array([40, 80, 80])
GREEN_HI = np.array([80, 255, 255])
RED1_LO  = np.array([0, 120, 80])
RED1_HI  = np.array([10, 255, 255])
RED2_LO  = np.array([170, 120, 80])
RED2_HI  = np.array([179, 255, 255])


def biggest(mask):
    mask = cv2.erode(mask, None, iterations=1)
    mask = cv2.dilate(mask, None, iterations=2)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return 0
    c = max(cnts, key=cv2.contourArea)
    area = cv2.contourArea(c)
    if area < 300:
        return 0
    return area


picam = Picamera2()
picam.configure(
    picam.create_preview_configuration(
        main={"size": (W, H), "format": "RGB888"},
        controls={"FrameRate": 15},
    )
)
picam.start()

print("Pillar avoid. Press 'q' to quit.")

try:
    # motor.forward(0.30)  # uncomment for a floor test
    while True:
        frame = picam.capture_array()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        gm = cv2.inRange(hsv, GREEN_LO, GREEN_HI)
        rm = cv2.inRange(hsv, RED1_LO, RED1_HI) + cv2.inRange(hsv, RED2_LO, RED2_HI)

        g_area = biggest(gm)
        r_area = biggest(rm)

        if r_area > MIN_AREA and r_area >= g_area:
            steer(-MAX_RIGHT_OFFSET)     # red -> right
            print("RED   -> RIGHT")
        elif g_area > MIN_AREA:
            steer(+MAX_LEFT_OFFSET)      # green -> left
            print("GREEN -> LEFT")
        else:
            steer(0)                     # straight
            print("straight")

        cv2.imshow("Avoid", frame)
        if cv2.waitKey(1) == ord("q"):
            break
finally:
    motor.stop()
    servo.detach()
    picam.stop()
    cv2.destroyAllWindows()
