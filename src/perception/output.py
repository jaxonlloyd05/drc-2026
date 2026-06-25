from core.types import Component, CameraData, State
import cv2

class CameraDisplay(Component):
  def __init__(self):
    self.save = None

  def show(self, data: CameraData, state: State) -> None:
    if not self.save:
      height, width = data.frame.shape[:2]
      fps = 30
      fourcc = cv2.VideoWriter_fourcc(*'mp4v')
      self.save = cv2.VideoWriter('output_video.mp4', fourcc, fps, (width, height))

    self.save.write(data.frame)

    if data.debug is not None:
      self._draw_debug(data)

    cv2.imshow('horse', data.frame)
    cv2.waitKey(1)

  def _draw_debug(self, data: CameraData) -> None:
    height, width = data.frame.shape[:2]
    for scanline in data.debug.scanlines:
      y = scanline.row
      cv2.line(data.frame, (0, y), (width - 1, y), (255, 255, 255), 1)
      if scanline.yellow_x is not None:
        cv2.circle(data.frame, (int(scanline.yellow_x), y), 6, (0, 255, 255), 1)
      if scanline.blue_x is not None:
        cv2.circle(data.frame, (int(scanline.blue_x), y), 6, (255, 0, 0), 1)
      if scanline.lane_center_x is not None:
        cv2.circle(data.frame, (int(scanline.lane_center_x), y), 5, (255, 255, 255), 1)

    cv2.line(data.frame, (width // 2, 0), (width // 2, height - 1), (255, 255, 255), 1)
  
  def cleanup(self) -> None:
    cv2.destroyAllWindows()  
