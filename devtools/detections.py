#!/usr/bin/env python3

'''
  same thing as motor_diff.py, from project root: `cp devtools/detections.py src/dt.py`, `python3 src/dt.py`
'''

from perception.camera import Camera
from perception.output import CameraDisplay

camera = Camera()
display = CameraDisplay()

try: 
  camera.start()

  while True:
    perception = camera.read()
    display.show(perception)

except KeyboardInterrupt:
  print('\n\n[EXIT] Putting robot to sleep...')

finally:
  camera.cleanup()
