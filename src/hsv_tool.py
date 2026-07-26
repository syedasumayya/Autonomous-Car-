"""
hsv_tool.py
-----------
Interactive HSV colour tuning tool. It is used to find the HSV range for the
red pillars, green pillars and magenta parking markers.

Run on the desktop (it opens windows). Three windows appear: Sliders, Camera, Mask.

How to use:
  1. Put a pillar in front of the camera (about 30-50 cm away).
  2. Adjust the H sliders until only the pillar is white in the Mask window.
  3. Raise 'S min' and 'V min' to remove pale or dark noise.
  4. Aim for: the pillar fully white, everything else black.
  5. Press 's' to print the values, then write them down.
  6. Repeat for each colour.

Note: red wraps around in HSV, so red needs two ranges
      (around H 0-10 and around H 170-179).
"""

from picamera2 import Picamera2
import cv2
import numpy as np

W, H = 320, 240

picam = Picamera2()
picam.configure(picam.create_preview_configuration(
    main={"size": (W, H), "format": "RGB888"}))
picam.start()


def nothing(x):
    pass


cv2.namedWindow("Sliders")
cv2.createTrackbar("H min", "Sliders", 0,   179, nothing)
cv2.createTrackbar("H max", "Sliders", 179, 179, nothing)
cv2.createTrackbar("S min", "Sliders", 0,   255, nothing)
cv2.createTrackbar("S max", "Sliders", 255, 255, nothing)
cv2.createTrackbar("V min", "Sliders", 0,   255, nothing)
cv2.createTrackbar("V max", "Sliders", 255, 255, nothing)

print("Adjust the sliders. 's' = print values, 'q' = quit.")

while True:
    frame = picam.capture_array()
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    hmin = cv2.getTrackbarPos("H min", "Sliders")
    hmax = cv2.getTrackbarPos("H max", "Sliders")
    smin = cv2.getTrackbarPos("S min", "Sliders")
    smax = cv2.getTrackbarPos("S max", "Sliders")
    vmin = cv2.getTrackbarPos("V min", "Sliders")
    vmax = cv2.getTrackbarPos("V max", "Sliders")

    lower = np.array([hmin, smin, vmin])
    upper = np.array([hmax, smax, vmax])
    mask = cv2.inRange(hsv, lower, upper)

    mask = cv2.erode(mask, None, iterations=1)
    mask = cv2.dilate(mask, None, iterations=2)

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if cnts:
        c = max(cnts, key=cv2.contourArea)
        area = cv2.contourArea(c)
        if area > 300:
            x, y, w, h = cv2.boundingRect(c)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 255, 0), 2)
            cv2.putText(frame, f"area:{int(area)} x:{x + w // 2}", (5, 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 0), 1)

    cv2.imshow("Camera", frame)
    cv2.imshow("Mask", mask)

    k = cv2.waitKey(1) & 0xFF
    if k == ord('s'):
        print(f"lower = np.array([{hmin}, {smin}, {vmin}])")
        print(f"upper = np.array([{hmax}, {smax}, {vmax}])")
    elif k == ord('q'):
        break

picam.stop()
cv2.destroyAllWindows()
