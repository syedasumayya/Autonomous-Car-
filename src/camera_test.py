"""
camera_test.py
--------------
Shows a live video window from the Raspberry Pi Camera.
Run on the desktop (not over plain SSH), then press 'q' to quit.

Status: tested and working.
"""

from picamera2 import Picamera2
import cv2

W, H = 320, 240   # small resolution = fast loop, enough detail for pillars

picam = Picamera2()
picam.configure(picam.create_preview_configuration(
    main={"size": (W, H), "format": "RGB888"}))
picam.start()

print("Live video. Press 'q' to quit.")

while True:
    frame = picam.capture_array()
    cv2.imshow("Camera", frame)
    if cv2.waitKey(1) == ord('q'):
        break

picam.stop()
cv2.destroyAllWindows()
