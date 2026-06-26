import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

try:
  import numpy as np
except ModuleNotFoundError:
  np = None

from core.types import CameraData
from perception.output import CameraDisplay


class FakeVideoWriter:
  instances = []

  def __init__(self, path, fourcc, fps, size):
    self.path = path
    self.fourcc = fourcc
    self.fps = fps
    self.size = size
    self.frames = []
    self.released = False
    FakeVideoWriter.instances.append(self)

  def isOpened(self):
    return True

  def write(self, frame):
    self.frames.append(frame)

  def release(self):
    self.released = True


def make_frame():
  if np is not None:
    return np.zeros((12, 16, 3), dtype=np.uint8)

  return types.SimpleNamespace(shape=(12, 16, 3))


def make_data():
  frame = make_frame()
  return CameraData(
    frame=frame,
    raw=frame,
    stop=False,
    confidence=1.0,
    turning=0.5,
  )


class CameraDisplayTest(unittest.TestCase):
  def setUp(self):
    FakeVideoWriter.instances = []

  @patch("perception.output.cv2.VideoWriter", FakeVideoWriter)
  @patch("perception.output.time.monotonic", side_effect=[0.0, 11.0])
  @patch("perception.output.datetime")
  def test_video_writer_rotates_segments(self, fake_datetime, _):
    fake_datetime.now.return_value.strftime.return_value = "20260626_120000"
    with tempfile.TemporaryDirectory() as tmpdir:
      display = CameraDisplay(headless=True)
      display.output_dir = Path(tmpdir)

      display.show(make_data())
      display.show(make_data())

    self.assertEqual(len(FakeVideoWriter.instances), 2)
    self.assertTrue(FakeVideoWriter.instances[0].released)
    self.assertFalse(FakeVideoWriter.instances[1].released)

  @patch("perception.output.cv2.VideoWriter", FakeVideoWriter)
  @patch("perception.output.time.monotonic", return_value=0.0)
  @patch("perception.output.datetime")
  def test_cleanup_releases_current_segment(self, fake_datetime, _):
    fake_datetime.now.return_value.strftime.return_value = "20260626_120000"
    with tempfile.TemporaryDirectory() as tmpdir:
      display = CameraDisplay(headless=True)
      display.output_dir = Path(tmpdir)

      display.show(make_data())
      display.cleanup()

    self.assertTrue(FakeVideoWriter.instances[0].released)


if __name__ == "__main__":
  unittest.main()
