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


class FakePi:
  instances = []

  def __init__(self):
    self.connected = True
    self.modes = []
    self.outputs = []
    self.pwm_frequencies = []
    self.pwm_ranges = []
    self.pwm_dutycycles = []
    self.stopped = False
    FakePi.instances.append(self)

  def set_mode(self, pin, mode):
    self.modes.append((pin, mode))

  def write(self, pin, value):
    self.outputs.append((pin, value))

  def set_PWM_frequency(self, pin, frequency):
    self.pwm_frequencies.append((pin, frequency))

  def set_PWM_range(self, pin, pwm_range):
    self.pwm_ranges.append((pin, pwm_range))

  def set_PWM_dutycycle(self, pin, dutycycle):
    self.pwm_dutycycles.append((pin, dutycycle))

  def stop(self):
    self.stopped = True


class FakePigpio(types.ModuleType):
  OUTPUT = "OUTPUT"

  def __init__(self):
    super().__init__("pigpio")

  def pi(self):
    return FakePi()


fake_pigpio = FakePigpio()
sys.modules["pigpio"] = fake_pigpio


from core.types import CameraData, MotorCommand, StateRules
from motor.translator import MotorTranslator
from motor.controller import (
  DEFAULT_PWM_RANGE,
  LEFT_MAX_DUTY,
  RIGHT_MAX_DUTY,
  MotorController,
  _board_to_bcm,
  _duty_percent_to_pwm,
)
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
    FakePi.instances = []
    self.controller = MotorController()

  def tearDown(self):
    self.controller.cleanup()

  @property
  def pi(self):
    return FakePi.instances[0]

  @property
  def left_pwm_pin(self):
    return _board_to_bcm(config.PIN_ENA)

  @property
  def right_pwm_pin(self):
    return _board_to_bcm(config.PIN_ENB)

  def last_pwm_duty(self, pin):
    return [duty for pwm_pin, duty in self.pi.pwm_dutycycles if pwm_pin == pin][-1]

  def test_initializes_outputs_and_pwm(self):
    expected_pins = [
      _board_to_bcm(config.PIN_ENA),
      _board_to_bcm(config.PIN_IN1),
      _board_to_bcm(config.PIN_IN2),
      _board_to_bcm(config.PIN_ENB),
      _board_to_bcm(config.PIN_IN3),
      _board_to_bcm(config.PIN_IN4),
    ]

    self.assertEqual(self.pi.modes, [(pin, fake_pigpio.OUTPUT) for pin in expected_pins])
    self.assertEqual(self.pi.pwm_frequencies, [
      (self.left_pwm_pin, 1000),
      (self.right_pwm_pin, 1000),
    ])
    self.assertEqual(self.pi.pwm_ranges, [
      (self.left_pwm_pin, DEFAULT_PWM_RANGE),
      (self.right_pwm_pin, DEFAULT_PWM_RANGE),
    ])

  def test_straight_command_sets_forward_baseline_duty(self):
    self.controller.execute(MotorCommand(turning_val=0.0, speed_val=1.0))

    self.assertEqual(self.last_pwm_duty(self.left_pwm_pin), _duty_percent_to_pwm(LEFT_MAX_DUTY))
    self.assertEqual(self.last_pwm_duty(self.right_pwm_pin), _duty_percent_to_pwm(RIGHT_MAX_DUTY))
    self.assertEqual(self.pi.outputs[-4:], [
      (_board_to_bcm(config.PIN_IN1), 1),
      (_board_to_bcm(config.PIN_IN2), 0),
      (_board_to_bcm(config.PIN_IN3), 1),
      (_board_to_bcm(config.PIN_IN4), 0),
    ])

  def test_full_right_turn_reverses_right_motor(self):
    self.controller.execute(MotorCommand(turning_val=1.0, speed_val=1.0))

    self.assertEqual(self.last_pwm_duty(self.left_pwm_pin), _duty_percent_to_pwm(LEFT_MAX_DUTY))
    self.assertEqual(self.last_pwm_duty(self.right_pwm_pin), _duty_percent_to_pwm(RIGHT_MAX_DUTY))
    self.assertEqual(self.pi.outputs[-4:], [
      (_board_to_bcm(config.PIN_IN1), 1),
      (_board_to_bcm(config.PIN_IN2), 0),
      (_board_to_bcm(config.PIN_IN3), 0),
      (_board_to_bcm(config.PIN_IN4), 1),
    ])

  def test_full_left_turn_reverses_left_motor(self):
    self.controller.execute(MotorCommand(turning_val=-1.0, speed_val=1.0))

    self.assertEqual(self.last_pwm_duty(self.left_pwm_pin), _duty_percent_to_pwm(LEFT_MAX_DUTY))
    self.assertEqual(self.last_pwm_duty(self.right_pwm_pin), _duty_percent_to_pwm(RIGHT_MAX_DUTY))
    self.assertEqual(self.pi.outputs[-4:], [
      (_board_to_bcm(config.PIN_IN1), 0),
      (_board_to_bcm(config.PIN_IN2), 1),
      (_board_to_bcm(config.PIN_IN3), 1),
      (_board_to_bcm(config.PIN_IN4), 0),
    ])

  def test_stop_command_sets_zero_duty_and_direction_pins_low(self):
    self.controller.execute(MotorCommand(turning_val=0.0, speed_val=0.0))

    self.assertEqual(self.last_pwm_duty(self.left_pwm_pin), 0)
    self.assertEqual(self.last_pwm_duty(self.right_pwm_pin), 0)
    self.assertEqual(self.pi.outputs[-4:], [
      (_board_to_bcm(config.PIN_IN1), 0),
      (_board_to_bcm(config.PIN_IN2), 0),
      (_board_to_bcm(config.PIN_IN3), 0),
      (_board_to_bcm(config.PIN_IN4), 0),
    ])

  def test_cleanup_stops_motors_pwm_and_gpio(self):
    self.controller.cleanup()

    self.assertEqual(self.last_pwm_duty(self.left_pwm_pin), 0)
    self.assertEqual(self.last_pwm_duty(self.right_pwm_pin), 0)
    self.assertTrue(self.pi.stopped)


if __name__ == "__main__":
  unittest.main()
