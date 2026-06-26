from core.types import Component, CameraData
import cv2
import time
from datetime import datetime
from pathlib import Path
import config

class CameraDisplay(Component):
  def __init__(self, headless: bool):
    self.save = None
    self.headless = headless
    self.output_dir = Path(config.VIDEO_OUTPUT_DIR)
    self.fps = config.VIDEO_FPS
    self.segment_seconds = max(1, config.VIDEO_SEGMENT_SECONDS)
    self.fourcc = cv2.VideoWriter_fourcc(*config.VIDEO_FOURCC)
    self.extension = config.VIDEO_EXTENSION
    self._segment_index = 0
    self._segment_started_at = 0.0
    self._video_size = None

  def show(self, data: CameraData) -> None:
    self._ensure_writer(data.frame)

    self.save.write(data.frame)

    if self.headless:
      return

    if data.debug is not None:
      self._draw_debug(data)

    cv2.imshow('horse', data.frame)
    cv2.waitKey(1)

  def _ensure_writer(self, frame) -> None:
    height, width = frame.shape[:2]
    size = (width, height)
    now = time.monotonic()

    segment_expired = (
      self.save is not None and
      now - self._segment_started_at >= self.segment_seconds
    )
    size_changed = self._video_size is not None and self._video_size != size

    if self.save is None or segment_expired or size_changed:
      self._open_segment(size, now)

  def _open_segment(self, size: tuple[int, int], started_at: float) -> None:
    if self.save:
      self.save.release()

    self.output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"output_{timestamp}_{self._segment_index:04d}{self.extension}"
    path = self.output_dir / filename

    self.save = cv2.VideoWriter(str(path), self.fourcc, self.fps, size)
    if hasattr(self.save, "isOpened") and not self.save.isOpened():
      raise RuntimeError(f"[ERROR] Failed to open video writer: {path}")

    self._segment_started_at = started_at
    self._video_size = size
    self._segment_index += 1

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
    if self.save:
      self.save.release()
      self.save = None

    if not self.headless:
      cv2.destroyAllWindows()  
