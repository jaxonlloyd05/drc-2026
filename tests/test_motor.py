import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

try:
  import numpy
except ModuleNotFoundError:
  fake_numpy = types.ModuleType("numpy")
  fake_numpy.ndarray = object
  sys.modules["numpy"] = fake_numpy


class FakePWM:
  instances = []

  def __init__(self, pin, frequency):
    self.pin = pin
    self.frequency = frequency
    self.duty_cycles = []
    self.started = False
    self.stopped = False
    FakePWM.instances.append(self)

  def start(self, duty):
    self.started = True
    self.duty_cycles.append(duty)

  def ChangeDutyCycle(self, duty):
    self.duty_cycles.append(duty)

  def stop(self):
    self.stopped = True


class FakeGPIO(types.ModuleType):
  BOARD = "BOARD"
  OUT = "OUT"
  HIGH = 1
  LOW = 0

  def __init__(self):
    super().__init__("RPi.GPIO")
    self.mode = None
    self.warnings = None
    self.setup_calls = []
    self.outputs = []
    self.cleaned_up = False
    self.PWM = FakePWM

  def setmode(self, mode):
    self.mode = mode

  def setwarnings(self, enabled):
    self.warnings = enabled

  def setup(self, pin, mode):
    self.setup_calls.append((pin, mode))

  def output(self, pin, value):
    self.outputs.append((pin, value))

  def cleanup(self):
    self.cleaned_up = True


fake_gpio = FakeGPIO()
fake_rpi = types.ModuleType("RPi")
fake_rpi.GPIO = fake_gpio
sys.modules["RPi"] = fake_rpi
sys.modules["RPi.GPIO"] = fake_gpio

from core.types import CameraData, MotorCommand, StateRules
from motor.translator import MotorTranslator
from motor.controller import MotorController
import config


def make_perception(turning=0.5, arrow=None):
  return CameraData(
    frame=None,
    raw=None,
    stop=False,
    confidence=1.0,
    turning=turning,
    arrow=arrow,
  )


class MotorTranslatorTest(unittest.TestCase):
  def setUp(self):
    self.translator = MotorTranslator()

  def test_centered_perception_goes_straight(self):
    rules = StateRules(speed_lim=1.0, turning_lim=1.0, obstacle_lim=0.0, ignore_arrows=True)

    command = self.translator.compute(make_perception(turning=0.5), rules)

    self.assertEqual(command.turning_val, 0.0)
    self.assertEqual(command.speed_val, 1.0)

  def test_left_and_right_perception_map_to_signed_turns(self):
    rules = StateRules(speed_lim=1.0, turning_lim=1.0, obstacle_lim=0.0, ignore_arrows=True)

    left = self.translator.compute(make_perception(turning=0.0), rules)
    right = self.translator.compute(make_perception(turning=1.0), rules)

    self.assertEqual(left.turning_val, -1.0)
    self.assertEqual(right.turning_val, 1.0)

  def test_speed_and_turning_limits_are_clamped(self):
    rules = StateRules(speed_lim=1.5, turning_lim=0.3, obstacle_lim=0.0, ignore_arrows=True)

    command = self.translator.compute(make_perception(turning=1.0), rules)

    self.assertEqual(command.speed_val, 1.0)
    self.assertEqual(command.turning_val, 0.3)

  def test_arrow_override_only_when_arrows_are_not_ignored(self):
    active_rules = StateRules(speed_lim=1.0, turning_lim=0.6, obstacle_lim=0.0, ignore_arrows=False)
    ignored_rules = StateRules(speed_lim=1.0, turning_lim=0.6, obstacle_lim=0.0, ignore_arrows=True)

    active = self.translator.compute(make_perception(turning=0.5, arrow=-1), active_rules)
    ignored = self.translator.compute(make_perception(turning=0.5, arrow=-1), ignored_rules)

    self.assertEqual(active.turning_val, -0.6)
    self.assertEqual(ignored.turning_val, 0.0)


class MotorControllerTest(unittest.TestCase):
  def setUp(self):
    FakePWM.instances = []
    fake_gpio.mode = None
    fake_gpio.warnings = None
    fake_gpio.setup_calls = []
    fake_gpio.outputs = []
    fake_gpio.cleaned_up = False
    self.controller = MotorController()

  def tearDown(self):
    self.controller.cleanup()

  @property
  def left_pwm(self):
    return FakePWM.instances[0]

  @property
  def right_pwm(self):
    return FakePWM.instances[1]

  def test_straight_command_sets_forward_baseline_duty(self):
    self.controller.execute(MotorCommand(turning_val=0.0, speed_val=1.0))

    self.assertEqual(self.left_pwm.duty_cycles[-1], 90.0)
    self.assertEqual(self.right_pwm.duty_cycles[-1], 95.0)
    self.assertEqual(fake_gpio.outputs[-4:], [
      (config.PIN_IN1, fake_gpio.HIGH),
      (config.PIN_IN2, fake_gpio.LOW),
      (config.PIN_IN3, fake_gpio.HIGH),
      (config.PIN_IN4, fake_gpio.LOW),
    ])

  def test_full_right_turn_reverses_right_motor(self):
    self.controller.execute(MotorCommand(turning_val=1.0, speed_val=1.0))

    self.assertEqual(self.left_pwm.duty_cycles[-1], 90.0)
    self.assertEqual(self.right_pwm.duty_cycles[-1], 95.0)
    self.assertEqual(fake_gpio.outputs[-4:], [
      (config.PIN_IN1, fake_gpio.HIGH),
      (config.PIN_IN2, fake_gpio.LOW),
      (config.PIN_IN3, fake_gpio.LOW),
      (config.PIN_IN4, fake_gpio.HIGH),
    ])

  def test_full_left_turn_reverses_left_motor(self):
    self.controller.execute(MotorCommand(turning_val=-1.0, speed_val=1.0))

    self.assertEqual(self.left_pwm.duty_cycles[-1], 90.0)
    self.assertEqual(self.right_pwm.duty_cycles[-1], 95.0)
    self.assertEqual(fake_gpio.outputs[-4:], [
      (config.PIN_IN1, fake_gpio.LOW),
      (config.PIN_IN2, fake_gpio.HIGH),
      (config.PIN_IN3, fake_gpio.HIGH),
      (config.PIN_IN4, fake_gpio.LOW),
    ])

  def test_stop_command_sets_zero_duty_and_direction_pins_low(self):
    self.controller.execute(MotorCommand(turning_val=0.0, speed_val=0.0))

    self.assertEqual(self.left_pwm.duty_cycles[-1], 0.0)
    self.assertEqual(self.right_pwm.duty_cycles[-1], 0.0)
    self.assertEqual(fake_gpio.outputs[-4:], [
      (config.PIN_IN1, fake_gpio.LOW),
      (config.PIN_IN2, fake_gpio.LOW),
      (config.PIN_IN3, fake_gpio.LOW),
      (config.PIN_IN4, fake_gpio.LOW),
    ])

  def test_cleanup_stops_motors_pwm_and_gpio(self):
    self.controller.cleanup()

    self.assertEqual(self.left_pwm.duty_cycles[-1], 0.0)
    self.assertEqual(self.right_pwm.duty_cycles[-1], 0.0)
    self.assertTrue(self.left_pwm.stopped)
    self.assertTrue(self.right_pwm.stopped)
    self.assertTrue(fake_gpio.cleaned_up)


if __name__ == "__main__":
  unittest.main()
