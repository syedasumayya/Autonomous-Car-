"""
ultra_test.py
-------------
Reads all four HC-SR04 ultrasonic sensors (front, left, right, back)
and prints their distances in centimetres.

Each Echo pin is protected by a 1 kΩ + 2 kΩ voltage divider so the Pi's
3.3 V GPIO input never sees the sensor's 5 V output level.

The pigpio pin factory is used for accurate timing. Make sure the pigpio
daemon is running before starting this script:

    sudo systemctl start pigpiod
"""

from gpiozero import DistanceSensor, Device
from gpiozero.pins.pigpio import PiGPIOFactory
import time
import warnings

warnings.filterwarnings("ignore")

Device.pin_factory = PiGPIOFactory()

front = DistanceSensor(echo=16, trigger=26, max_distance=2.0)
left  = DistanceSensor(echo=6,  trigger=5,  max_distance=2.0)
right = DistanceSensor(echo=19, trigger=13, max_distance=2.0)
back  = DistanceSensor(echo=8,  trigger=22, max_distance=2.0)


def read(sensor):
    """Return distance in centimetres. -1 if the read timed out."""
    try:
        return sensor.distance * 100
    except Exception:
        return -1


print("All 4 sensors. Ctrl+C to quit.")
try:
    while True:
        f = read(front)
        l = read(left)
        r = read(right)
        b = read(back)
        print(f"F:{f:5.1f}  L:{l:5.1f}  R:{r:5.1f}  B:{b:5.1f}")
        time.sleep(0.3)
except KeyboardInterrupt:
    print("\ndone")
