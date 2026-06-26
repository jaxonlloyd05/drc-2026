#!/usr/bin/env python3

'''
  From the project root: `python3 devtools/detections.py`
'''

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from perception.camera import Camera
from perception.output import CameraDisplay

parser = argparse.ArgumentParser(description="Display camera detections without motor control.")
parser.add_argument("--headless", action="store_true", help="record output without opening display windows")
args = parser.parse_args()

camera = Camera(headless=args.headless)
display = CameraDisplay(headless=args.headless)

try: 
  camera.start()

  while True:
    perception = camera.read()
    display.show(perception)

except KeyboardInterrupt:
  print('\n\n[EXIT] Putting robot to sleep...')

finally:
  camera.cleanup()
  display.cleanup()
