"""
detect.py
---------
Detects the red and green pillars from the camera and reports, for the
nearest one, its colour, its horizontal position (x) and its size (area).

- Red pillars must be passed on the RIGHT.
- Green pillars must be passed on the LEFT.

Red needs two HSV ranges because red wraps around in the HSV colour wheel
(it appears near H 0 and near H 179).

Run on the desktop (it opens a window). Press 'q' to quit.

Status: tested and working.
"""

from picamera2 import Picamera2
import cv2
import numpy as np

W, H = 320, 240
MIN_AREA = 500   # smaller than this is treated as noise and ignored

# HSV ranges (tuned with hsv_tool.py)
GREEN_LO = np.array([40, 80, 80])
GREEN_HI = np.array([80, 255, 255])

RED1_LO = np.array([0, 120, 80])       # red range 1 (near H 0)
RED1_HI = np.array([10, 255, 255])
RED2_LO = np.array([170, 120, 80])     # red range 2 (near H 179)
RED2_HI = np.array([179, 255, 255])


def biggest(mask):
    """Return (area, centre_x, bounding_box) of the largest blob, or zeros."""
    mask = cv2.erode(mask, None, iterations=1)
    mask = cv2.dilate(mask, None, iterations=2)
    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return 0, 0, None
    c = max(cnts, key=cv2.contourArea)
    area = cv2.contourArea(c)
    if area < MIN_AREA:
        return 0, 0, None
    x, y, w, h = cv2.boundingRect(c)
    return area, x + w // 2, (x, y, w, h)


picam = Picamera2()
picam.configure(picam.create_preview_configuration(
    main={"size": (W, H), "format": "RGB888"}))
picam.start()

print("Pillar detection. Press 'q' to quit.")

while True:
    frame = picam.capture_array()
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    green_mask = cv2.inRange(hsv, GREEN_LO, GREEN_HI)
    red_mask = cv2.inRange(hsv, RED1_LO, RED1_HI) + \
               cv2.inRange(hsv, RED2_LO, RED2_HI)

    g_area, g_x, g_box = biggest(green_mask)
    r_area, r_x, r_box = biggest(red_mask)

    # Handle the nearer pillar first (larger area = nearer).
    if r_area > g_area and r_area > 0:
        print(f"RED   | x:{r_x}  area:{int(r_area)}  -> keep RIGHT")
        x, y, w, h = r_box
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 2)
    elif g_area > 0:
        print(f"GREEN | x:{g_x}  area:{int(g_area)}  -> keep LEFT")
        x, y, w, h = g_box
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
    else:
        print("no pillar")

    cv2.imshow("Detection", frame)
    if cv2.waitKey(1) == ord('q'):
        break

picam.stop()
cv2.destroyAllWindows()
