from core.types import Component, CameraData
from perception.vision import VisionProcessor
from collections import deque
import cv2
import numpy as np
import config

MAXFRAMES = config.FRAME_AVERAGE_COUNT

class Camera(Component):
  def __init__(self, processor: VisionProcessor | None = None):
    self.index = config.CAMERA_INDEX
    self.cap = None
    self.prevframes = deque([], maxlen=MAXFRAMES)
    self.processor = processor or VisionProcessor()

  def spinup(self) -> None:
    while len(self.prevframes) < MAXFRAMES:
      if not self.cap:
        raise RuntimeError('[ERROR] Camera has not been initialised')
      
      ret, raw = self.cap.read()
      if not ret:
        raise RuntimeError('[ERROR] Failed to read frame during camera spinup')
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
    if not ret:
      raise RuntimeError('[ERROR] Failed to read frame')

    self.prevframes.append(raw)
    averaged = self._averaged_frame()
    return self.processor.process(averaged, raw=raw)

  def _averaged_frame(self) -> np.ndarray:
    averaged = np.mean(np.array(self.prevframes, dtype=np.float32), axis=0).astype(np.uint8)
    return cv2.GaussianBlur(averaged, (5, 5), 0)


  def cleanup(self) -> None:
    if self.cap:
      self.cap.release()

    cv2.destroyAllWindows()

    print('[EXIT] Cleaned up camera!')

    
