from core.types import Component, CameraData
import cv2

class Camera(Component):
  def __init__(self):
    self.index = 0    # will get index from config.py when i make it later on
    self.cap = None

  def start(self) -> None:
    self.cap = cv2.VideoCapture(self.index)

    if not self.cap.isOpened():
      raise RuntimeError('[ERROR] Failed to open camera')
    
    print('[START] Started camera')

  def read(self) -> CameraData:
    if not self.cap:
      raise RuntimeError('[ERROR] Camera has not been initialised')

    ret, frame = self.cap.read()

    if not ret:
      raise RuntimeError('[ERROR] Failed to read frame')
    
    return CameraData(frame=frame, stop=False, confidence=1.0, turning=0.0)

  def cleanup(self) -> None:
    if self.cap:
      self.cap.release()

    cv2.destroyAllWindows()

    print('[EXIT] Cleaned up camera!')

    