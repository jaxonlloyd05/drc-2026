from collections import deque
from dataclasses import dataclass

import cv2
import numpy as np

import config
from core.shared import HSV_RANGES
from core.types import CameraData, ScanlineDebug, VisionDebug


@dataclass
class VisionConfig:
  crop_mode: str = config.CAMERA_CROP_MODE
  flip_code: int | None = config.CAMERA_FLIP_CODE
  scanline_ratios: tuple[float, ...] = config.SCANLINE_RATIOS
  scanline_weights: tuple[float, ...] = config.SCANLINE_WEIGHTS
  min_tape_run_width_px: int = config.MIN_TAPE_RUN_WIDTH_PX
  scanline_band_height_px: int = config.SCANLINE_BAND_HEIGHT_PX
  default_lane_width_ratio: float = config.DEFAULT_LANE_WIDTH_RATIO
  min_lane_width_ratio: float = config.MIN_LANE_WIDTH_RATIO
  max_lane_width_ratio: float = config.MAX_LANE_WIDTH_RATIO
  smoothing_frames: int = config.VISION_SMOOTHING_FRAMES


@dataclass
class _Scanline:
  row: int
  yellow_x: float | None
  blue_x: float | None
  lane_center_x: float | None
  confidence: float


class VisionProcessor:
  def __init__(self, cfg: VisionConfig | None = None):
    self.cfg = cfg or VisionConfig()
    self._turning_history = deque([], maxlen=self.cfg.smoothing_frames)
    self._confidence_history = deque([], maxlen=self.cfg.smoothing_frames)
    self._last_lane_width: float | None = None

  def process(self, frame: np.ndarray, raw: np.ndarray | None = None) -> CameraData:
    raw_frame = raw if raw is not None else frame
    transformed = self._transform(frame)
    masks = self._build_masks(transformed)
    scanlines = self._scanlines(masks["yellow"], masks["blue"], transformed.shape)
    raw_turning, raw_confidence = self._estimate_motion(scanlines, transformed.shape[1])
    turning = self._smooth(raw_turning, self._turning_history)
    confidence = self._smooth(raw_confidence, self._confidence_history)
    stop = self._detect_stop(masks["green"])
    arrow = self._detect_arrow(masks["black"])
    debug = VisionDebug(
      scanlines=[
        ScanlineDebug(
          row=i.row,
          yellow_x=i.yellow_x,
          blue_x=i.blue_x,
          lane_center_x=i.lane_center_x,
          confidence=i.confidence,
        )
        for i in scanlines
      ],
      stop=stop,
      arrow=arrow,
      raw_turning=raw_turning,
      raw_confidence=raw_confidence,
    )

    annotated = self.annotate(transformed, debug)
    return CameraData(
      frame=annotated,
      raw=raw_frame,
      stop=stop,
      confidence=confidence,
      turning=turning,
      arrow=arrow,
      debug=debug,
    )

  def annotate(self, frame: np.ndarray, debug: VisionDebug) -> np.ndarray:
    annotated = frame.copy()
    h, w = annotated.shape[:2]

    for scanline in debug.scanlines:
      y = scanline.row
      cv2.line(annotated, (0, y), (w - 1, y), (230, 230, 230), 1)

      if scanline.yellow_x is not None:
        cv2.circle(annotated, (int(scanline.yellow_x), y), 5, (0, 255, 255), -1)

      if scanline.blue_x is not None:
        cv2.circle(annotated, (int(scanline.blue_x), y), 5, (255, 0, 0), -1)

      if scanline.lane_center_x is not None:
        cv2.circle(annotated, (int(scanline.lane_center_x), y), 4, (255, 255, 255), -1)

    cv2.line(annotated, (w // 2, 0), (w // 2, h - 1), (255, 255, 255), 1)
    text = f"conf={debug.raw_confidence:.2f} turn={debug.raw_turning:.2f}"
    if debug.stop:
      text += " stop"
    if debug.arrow is not None:
      text += f" arrow={debug.arrow}"
    cv2.putText(annotated, text, (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
    return annotated

  def _transform(self, frame: np.ndarray) -> np.ndarray:
    transformed = frame
    _, w = transformed.shape[:2]

    if self.cfg.crop_mode == "left_half":
      transformed = transformed[:, :w // 2]
    elif self.cfg.crop_mode == "right_half":
      transformed = transformed[:, w // 2:]
    elif self.cfg.crop_mode != "full":
      raise ValueError(f"Unsupported crop mode: {self.cfg.crop_mode}")

    if self.cfg.flip_code is not None:
      transformed = cv2.flip(transformed, self.cfg.flip_code)

    return transformed

  def _build_masks(self, frame: np.ndarray) -> dict[str, np.ndarray]:
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    masks = {
      "yellow": cv2.inRange(hsv, HSV_RANGES.YLW_LOW, HSV_RANGES.YLW_HIGH),
      "blue": cv2.inRange(hsv, HSV_RANGES.BLU_LOW, HSV_RANGES.BLU_HIGH),
      "green": cv2.inRange(hsv, HSV_RANGES.GRN_LOW, HSV_RANGES.GRN_HIGH),
      "black": cv2.inRange(hsv, HSV_RANGES.BLK_LOW, HSV_RANGES.BLK_HIGH),
    }

    return {name: self._clean_mask(mask) for name, mask in masks.items()}

  def _clean_mask(self, mask: np.ndarray) -> np.ndarray:
    open_kernel = np.ones((3, 3), np.uint8)
    close_kernel = np.ones((7, 7), np.uint8)
    opened = cv2.morphologyEx(mask, cv2.MORPH_OPEN, open_kernel)
    return cv2.morphologyEx(opened, cv2.MORPH_CLOSE, close_kernel)

  def _scanlines(
    self,
    yellow_mask: np.ndarray,
    blue_mask: np.ndarray,
    shape: tuple[int, ...],
  ) -> list[_Scanline]:
    h, w = shape[:2]
    scanlines = []

    for ratio in self.cfg.scanline_ratios:
      row = int(np.clip(round(h * ratio), 0, h - 1))
      yellow_runs = self._runs_at_row(yellow_mask, row)
      blue_runs = self._runs_at_row(blue_mask, row)
      yellow_x, blue_x = self._choose_boundaries(yellow_runs, blue_runs, w)
      lane_center_x, confidence = self._lane_center(yellow_x, blue_x, w)
      scanlines.append(_Scanline(row, yellow_x, blue_x, lane_center_x, confidence))

    return scanlines

  def _runs_at_row(self, mask: np.ndarray, row: int) -> list[tuple[int, int, int]]:
    h, _ = mask.shape[:2]
    half_band = max(1, self.cfg.scanline_band_height_px // 2)
    y0 = max(0, row - half_band)
    y1 = min(h, row + half_band + 1)
    band = mask[y0:y1, :]
    active = np.count_nonzero(band, axis=0) >= max(1, (y1 - y0) // 3)
    indices = np.flatnonzero(active)

    if len(indices) == 0:
      return []

    splits = np.where(np.diff(indices) > 1)[0] + 1
    groups = np.split(indices, splits)
    runs = []

    for group in groups:
      start = int(group[0])
      end = int(group[-1])
      width = end - start + 1
      if width >= self.cfg.min_tape_run_width_px:
        runs.append((start, end, width))

    return runs

  def _choose_boundaries(
    self,
    yellow_runs: list[tuple[int, int, int]],
    blue_runs: list[tuple[int, int, int]],
    width: int,
  ) -> tuple[float | None, float | None]:
    yellow_x = self._largest_run_center(yellow_runs)
    blue_x = self._largest_run_center(blue_runs)

    if yellow_x is None or blue_x is None:
      return yellow_x, blue_x

    if yellow_x < blue_x:
      return yellow_x, blue_x

    pair = self._best_ordered_pair(yellow_runs, blue_runs, width)
    if pair is not None:
      return pair

    yellow_width = max(run[2] for run in yellow_runs)
    blue_width = max(run[2] for run in blue_runs)
    return (yellow_x, None) if yellow_width >= blue_width else (None, blue_x)

  def _largest_run_center(self, runs: list[tuple[int, int, int]]) -> float | None:
    if not runs:
      return None

    start, end, _ = max(runs, key=lambda run: run[2])
    return (start + end) / 2

  def _best_ordered_pair(
    self,
    yellow_runs: list[tuple[int, int, int]],
    blue_runs: list[tuple[int, int, int]],
    width: int,
  ) -> tuple[float, float] | None:
    min_width = width * self.cfg.min_lane_width_ratio
    max_width = width * self.cfg.max_lane_width_ratio
    best_pair = None
    best_score = -1

    for yellow in yellow_runs:
      yellow_x = (yellow[0] + yellow[1]) / 2
      for blue in blue_runs:
        blue_x = (blue[0] + blue[1]) / 2
        lane_width = blue_x - yellow_x
        if min_width <= lane_width <= max_width:
          score = yellow[2] + blue[2]
          if score > best_score:
            best_score = score
            best_pair = (yellow_x, blue_x)

    return best_pair

  def _lane_center(
    self,
    yellow_x: float | None,
    blue_x: float | None,
    width: int,
  ) -> tuple[float | None, float]:
    min_width = width * self.cfg.min_lane_width_ratio
    max_width = width * self.cfg.max_lane_width_ratio

    if yellow_x is not None and blue_x is not None:
      lane_width = blue_x - yellow_x
      if min_width <= lane_width <= max_width:
        if self._last_lane_width is None:
          self._last_lane_width = lane_width
        else:
          self._last_lane_width = (self._last_lane_width * 0.75) + (lane_width * 0.25)
        return (yellow_x + blue_x) / 2, 1.0

      return None, 0.0

    inferred_width = self._last_lane_width or width * self.cfg.default_lane_width_ratio
    inferred_width = float(np.clip(inferred_width, min_width, max_width))

    if yellow_x is not None:
      return yellow_x + inferred_width / 2, 0.55

    if blue_x is not None:
      return blue_x - inferred_width / 2, 0.55

    return None, 0.0

  def _estimate_motion(self, scanlines: list[_Scanline], width: int) -> tuple[float, float]:
    weighted_center = 0.0
    weighted_confidence = 0.0
    active_weight = 0.0
    total_weight = float(sum(self.cfg.scanline_weights))

    for scanline, weight in zip(scanlines, self.cfg.scanline_weights):
      weighted_confidence += scanline.confidence * weight
      if scanline.lane_center_x is not None:
        weighted_center += scanline.lane_center_x * scanline.confidence * weight
        active_weight += scanline.confidence * weight

    confidence = weighted_confidence / total_weight if total_weight else 0.0

    if active_weight <= 0:
      return 0.5, 0.0

    lane_center = weighted_center / active_weight
    offset = (lane_center - (width / 2)) / (width / 2)
    turning = 0.5 + (offset * 0.5)
    return float(np.clip(turning, 0.0, 1.0)), float(np.clip(confidence, 0.0, 1.0))

  def _smooth(self, value: float, history: deque[float]) -> float:
    history.append(value)
    return float(np.mean(history))

  def _detect_stop(self, green_mask: np.ndarray) -> bool:
    h, w = green_mask.shape[:2]
    roi = green_mask[int(h * 0.68):, :]
    contours, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    for contour in contours:
      x, y, cw, ch = cv2.boundingRect(contour)
      area = cv2.contourArea(contour)
      if cw >= w * 0.45 and ch <= h * 0.18 and area >= w * h * 0.004:
        return True

    return False

  def _detect_arrow(self, black_mask: np.ndarray) -> int | None:
    h, w = black_mask.shape[:2]
    y0 = int(h * 0.25)
    y1 = int(h * 0.88)
    x0 = int(w * 0.12)
    x1 = int(w * 0.88)
    roi = black_mask[y0:y1, x0:x1]
    contours, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
      return None

    contour = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(contour)
    if area < w * h * 0.008:
      return None

    x, y, cw, ch = cv2.boundingRect(contour)
    if cw <= 0 or ch <= 0:
      return None

    aspect = cw / ch
    fill = area / (cw * ch)
    if aspect < 1.15 or not 0.18 <= fill <= 0.85:
      return None

    moments = cv2.moments(contour)
    if moments["m00"] == 0:
      return None

    centroid_x = moments["m10"] / moments["m00"]
    left_extent = centroid_x - x
    right_extent = (x + cw) - centroid_x
    threshold = cw * 0.02

    if right_extent > left_extent + threshold:
      return 1
    if left_extent > right_extent + threshold:
      return -1

    return None
