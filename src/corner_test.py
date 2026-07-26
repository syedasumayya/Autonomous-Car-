"""
corner_test.py
--------------
Drives forward, then executes a 90 deg turn whenever the front sensor
sees a wall closer than FRONT_LIMIT. The turn direction is decided the
first time a corner is reached: whichever side has more free space is
chosen and then reused for every subsequent corner. This matches the
WRO track where all four corners share the same handedness on any given
attempt.

The turn itself is closed on the yaw angle from the MPU6050 gyroscope
rather than on time, so the vehicle stops at a consistent 90 deg
regardless of battery voltage or floor friction.

Key parameters to tune per vehicle:

    FRONT_LIMIT    -- how far ahead the wall is when the turn begins.
                      Bigger = start the turn earlier.
    TURN_SPEED     -- forward speed during the turn.
    Turn threshold -- the '>= 80' in turn_90() stops slightly short of
                      90 deg to compensate for momentum. Increase toward
                      90 if the vehicle finishes under-rotated.
    BOOST / BOOST_TIME -- brief high-PWM kick to get the TT motor moving
                          from a standing start.
"""

from gpiozero import DistanceSensor, Motor, AngularServo, Device
from gpiozero.pins.pigpio import PiGPIOFactory
from mpu6050 import mpu6050
import time
import warnings

warnings.filterwarnings("ignore")

Device.pin_factory = PiGPIOFactory()

# ----- SENSORS -----
left  = DistanceSensor(echo=6,  trigger=5,  max_distance=2.0)
right = DistanceSensor(echo=19, trigger=13, max_distance=2.0)
front = DistanceSensor(echo=16, trigger=26, max_distance=2.0)

# ----- STEERING GEOMETRY -----
STRAIGHT_ANGLE = 10
LEFT_ANGLE     = 90
RIGHT_ANGLE    = -23
MAX_LEFT_OFFSET  = LEFT_ANGLE - STRAIGHT_ANGLE
MAX_RIGHT_OFFSET = STRAIGHT_ANGLE - RIGHT_ANGLE

# ----- DRIVING PARAMETERS -----
SPEED       = 0.32
BOOST       = 1.0          # brief kick to overcome static friction
BOOST_TIME  = 0.3
TURN_SPEED  = 0.25
FRONT_LIMIT = 45           # cm: how close before we start turning

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
    """Integrate gyro Z over dt to keep a running heading."""
    global angle, last_t
    now = time.time()
    dt = now - last_t
    last_t = now
    gz = mpu.get_gyro_data()["z"] - BIAS
    angle += gz * dt


def drive_forward(speed):
    """Brief high-PWM boost so the TT motor actually starts."""
    motor.forward(BOOST)
    time.sleep(BOOST_TIME)
    motor.forward(speed)


def turn_90(direction):
    """direction: +1 = left, -1 = right. Closed on gyro angle."""
    global angle
    start_angle = angle
    print(f"TURN {'LEFT' if direction > 0 else 'RIGHT'} from {start_angle:.1f}")

    if direction > 0:
        steer(+MAX_LEFT_OFFSET)
    else:
        steer(-MAX_RIGHT_OFFSET)

    motor.forward(BOOST)
    time.sleep(0.2)
    motor.forward(TURN_SPEED)

    while True:
        update_angle()
        turned = abs(angle - start_angle)
        print(f"  angle:{angle:+7.1f}  turned:{turned:5.1f}")
        if turned >= 80:
            break
        time.sleep(0.02)

    steer(0)
    motor.stop()
    time.sleep(0.3)
    print(f"TURN done. angle:{angle:.1f}")


# ----- MAIN LOOP -----
print("\nRunning. Ctrl+C to stop.\n")
time.sleep(1)

turn_direction = None
drive_forward(SPEED)

try:
    while True:
        update_angle()
        f = read(front)
        l = read(left)
        r = read(right)

        if f < FRONT_LIMIT:
            if turn_direction is None:
                if l > r:
                    turn_direction = +1
                    print(f"Direction locked: LEFT  (L:{l:.0f} R:{r:.0f})")
                else:
                    turn_direction = -1
                    print(f"Direction locked: RIGHT (L:{l:.0f} R:{r:.0f})")

            motor.stop()
            time.sleep(0.2)
            turn_90(turn_direction)
            drive_forward(SPEED)
            time.sleep(0.3)
        else:
            steer(0)
            print(f"straight  F:{f:.0f}  angle:{angle:+.1f}")

        time.sleep(0.05)
finally:
    motor.stop()
    servo.detach()
    print("done")
