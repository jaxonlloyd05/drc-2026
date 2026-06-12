from core.types import Component, CameraData
from core.shared import HSV_RANGES
from collections import deque
from dataclasses import dataclass
import cv2
import numpy as np

MAXFRAMES = 2

class Camera(Component):
  def __init__(self):
    self.index = 0    # will get index from config.py when i make it later on
    self.cap = None
    self.prevframes = deque([], maxlen=MAXFRAMES)

  def spinup(self) -> None:
    while len(self.prevframes) < MAXFRAMES:
      if not self.cap:
        raise RuntimeError('[ERROR] Camera has not been initialised')
      
      ret, raw = self.cap.read()
      self.prevframes.append(raw)


  def start(self) -> None:
    self.cap = cv2.VideoCapture(self.index)

    if not self.cap.isOpened():
      raise RuntimeError('[ERROR] Failed to open camera')
    
    print('[START] Started camera')

  def read(self) -> CameraData:
    if not self.cap:
      raise RuntimeError('[ERROR] Camera has not been initialised')
    
    if len(self.prevframes) < MAXFRAMES:
      self.spinup()
    
    ret, raw = self.cap.read()
    self.prevframes.append(raw)
    frame = self.filter()

    if not ret:
      raise RuntimeError('[ERROR] Failed to read frame')
    
    return CameraData(
      frame=frame, 
      raw=raw, 
      stop=False, 
      confidence=1.0, 
      turning=0.0
      )

  def filter(self):
    avgd = np.mean(np.array(self.prevframes, dtype=np.float32), axis=0).astype(np.uint8)
    blur = cv2.GaussianBlur(avgd, (5, 5), 0)
    _, w = blur.shape[:2]
    frame = cv2.flip(blur[:, :w // 2], -1)

    hsvs = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    blue_mask = cv2.inRange(hsvs, HSV_RANGES.BLU_LOW, HSV_RANGES.BLU_HIGH)
    yellow_mask = cv2.inRange(hsvs, HSV_RANGES.YLW_LOW, HSV_RANGES.YLW_HIGH)
    green_mask = cv2.inRange(hsvs, HSV_RANGES.GRN_LOW, HSV_RANGES.GRN_HIGH)

    comb_mask = cv2.bitwise_or(green_mask, cv2.bitwise_or(yellow_mask, blue_mask))
    grey_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    grey_frame = cv2.cvtColor(grey_frame, cv2.COLOR_GRAY2BGR)
    processed = np.where(comb_mask[:, :, np.newaxis] > 0, frame, grey_frame)

    ylw_mnms = cv2.moments(yellow_mask)
    blue_mnms = cv2.moments(blue_mask)

    return processed


  def cleanup(self) -> None:
    if self.cap:
      self.cap.release()

    cv2.destroyAllWindows()

    print('[EXIT] Cleaned up camera!')

    