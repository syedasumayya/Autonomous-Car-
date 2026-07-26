"""
combined.py
-----------
Combines lane following, corner turns, and pillar avoidance into a
single behaviour loop for the Obstacle Challenge.

Priority order (highest first) on every tick:

    1. A pillar in view       -> pass on the correct side
                                    red   -> keep RIGHT
                                    green -> keep LEFT
    2. Front wall < FRONT_LIMIT -> 90 deg turn, direction locked on the
                                   first corner from the L/R sensors.
    3. Otherwise                -> proportional lane hold between the
                                   left and right walls.

The camera is polled every tick but is only actioned when a coloured
blob larger than MIN_AREA is present. Blob size stands in for distance:
the pillar has to be reasonably close before the vehicle deviates.

Prerequisites:
    - I2C enabled (for the MPU6050)
    - pigpio daemon running: `sudo systemctl start pigpiod`
    - IMU calibration is repeated at every start-up; keep the vehicle
      still during the "Calibrating IMU" message.
"""

from picamera2 import Picamera2
from gpiozero import DistanceSensor, Motor, AngularServo, Device
from gpiozero.pins.pigpio import PiGPIOFactory
from mpu6050 import mpu6050
import cv2
import numpy as np
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
STRAIGHT_ANGLE = 10
LEFT_ANGLE     = 90
RIGHT_ANGLE    = -23
MAX_LEFT_OFFSET  = LEFT_ANGLE - STRAIGHT_ANGLE
MAX_RIGHT_OFFSET = STRAIGHT_ANGLE - RIGHT_ANGLE

# ----- DRIVING PARAMETERS -----
SPEED       = 0.32
TURN_SPEED  = 0.25
Kp_LANE     = 2.5
Kp_PILLAR   = 40           # steering offset applied on a pillar sighting

TARGET_SIDE = 25
WALL_MAX    = 80
FRONT_LIMIT = 45
BACK_LIMIT  = 15
MIN_AREA    = 800          # pixels: minimum coloured blob to react to

# ----- ACTUATORS -----
motor = Motor(forward=23, backward=24, enable=12, pwm=True)
servo = AngularServo(
    18,
    min_angle=-90, max_angle=90,
    min_pulse_width=0.0005, max_pulse_width=0.0025,
)


def steer(direction):
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


def kickstart(speed):
    motor.forward(1.0)
    time.sleep(0.3)
    motor.forward(speed)


# ----- IMU -----
mpu = mpu6050(0x68)

print("Calibrating IMU. Keep still ~2 s...")
time.sleep(1)
bias_sum = 0.0
for _ in range(100):
    bias_sum += mpu.get_gyro_data()["z"]
    time.sleep(0.01)
BIAS = bias_sum / 100
print(f"Bias: {BIAS:+.3f}")

angle = 0.0
last_t = time.time()


def update_angle():
    global angle, last_t
    now = time.time()
    dt = now - last_t
    last_t = now
    gz = mpu.get_gyro_data()["z"] - BIAS
    angle += gz * dt


def turn_90(direction):
    global angle
    start_angle = angle
    print(f"TURN {'LEFT' if direction > 0 else 'RIGHT'}")

    if direction > 0:
        steer(+MAX_LEFT_OFFSET)
    else:
        steer(-MAX_RIGHT_OFFSET)

    motor.forward(1.0)
    time.sleep(0.2)
    motor.forward(TURN_SPEED)

    while True:
        update_angle()
        if abs(angle - start_angle) >= 80:
            break
        time.sleep(0.02)

    steer(0)
    motor.stop()
    time.sleep(0.3)


# ----- CAMERA / COLOUR RANGES -----
W, H = 320, 240

# Green (single HSV range)
GREEN_LO = np.array([40, 80, 80])
GREEN_HI = np.array([80, 255, 255])

# Red wraps around the HSV hue circle, so two ranges are OR'd together.
RED1_LO = np.array([0, 120, 80])
RED1_HI = np.array([10, 255, 255])
RED2_LO = np.array([170, 120, 80])
RED2_HI = np.array([179, 255, 255])


def biggest(mask):
    """Return the area of the largest contour in the mask."""
    mask = cv2.erode(mask, None, iterations=1)
    mask = cv2.dilate(mask, None, iterations=2)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return 0
    return cv2.contourArea(max(cnts, key=cv2.contourArea))


picam = Picamera2()
picam.configure(
    picam.create_preview_configuration(
        main={"size": (W, H), "format": "RGB888"},
        controls={"FrameRate": 15},
    )
)
picam.start()

# ----- MAIN LOOP -----
print("\nCombined behaviour. Ctrl+C to stop.\n")
time.sleep(1)

turn_direction = None
kickstart(SPEED)

try:
    while True:
        update_angle()
        f = read(front)
        l = read(left)
        r = read(right)

        # ---- 1. Pillar avoidance (highest priority) ----
        frame = picam.capture_array()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        r_mask = cv2.inRange(hsv, RED1_LO, RED1_HI) + cv2.inRange(hsv, RED2_LO, RED2_HI)
        g_mask = cv2.inRange(hsv, GREEN_LO, GREEN_HI)
        r_area = biggest(r_mask)
        g_area = biggest(g_mask)

        if r_area > MIN_AREA and r_area >= g_area:
            # Red pillar: pass on the RIGHT -> negative steer.
            steer(-Kp_PILLAR)
            motor.forward(SPEED)
            print(f"PILLAR-R a:{int(r_area)}")
            time.sleep(0.05)
            continue

        if g_area > MIN_AREA:
            # Green pillar: pass on the LEFT -> positive steer.
            steer(+Kp_PILLAR)
            motor.forward(SPEED)
            print(f"PILLAR-G a:{int(g_area)}")
            time.sleep(0.05)
            continue

        # ---- 2. Corner ----
        if f < FRONT_LIMIT:
            if turn_direction is None:
                turn_direction = +1 if l > r else -1
                print(f"Direction locked: {'LEFT' if turn_direction > 0 else 'RIGHT'}")

            motor.stop()
            time.sleep(0.2)
            turn_90(turn_direction)
            kickstart(SPEED)
            time.sleep(0.3)
            continue

        # ---- 3. Lane follow ----
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

        steering = Kp_LANE * error
        steer(steering)
        print(f"LANE  L:{l:.0f} R:{r:.0f} F:{f:.0f} st:{steering:.0f}")
        time.sleep(0.05)
finally:
    motor.stop()
    servo.detach()
    picam.stop()
    print("done")
