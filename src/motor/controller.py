from core.types import Component, MotorCommand

import pigpio
import config

DEFAULT_PWM_HZ = 1000
DEFAULT_PWM_RANGE = 10000
LEFT_MAX_DUTY = 90.8
RIGHT_MAX_DUTY = 97.0

BOARD_TO_BCM = {
  3: 2,
  5: 3,
  7: 4,
  8: 14,
  10: 15,
  11: 17,
  12: 18,
  13: 27,
  15: 22,
  16: 23,
  18: 24,
  19: 10,
  21: 9,
  22: 25,
  23: 11,
  24: 8,
  26: 7,
  29: 5,
  31: 6,
  32: 12,
  33: 13,
  35: 19,
  36: 16,
  37: 26,
  38: 20,
  40: 21,
}


def _clamp(value: float, low: float, high: float) -> float:
  return max(low, min(high, value))


def _board_to_bcm(pin: int) -> int:
  try:
    return BOARD_TO_BCM[pin]
  except KeyError as exc:
    raise ValueError(f"Board pin {pin} is not mapped to a Raspberry Pi BCM GPIO") from exc


def _duty_percent_to_pwm(duty: float) -> int:
  return round((_clamp(abs(duty), 0.0, 100.0) / 100.0) * DEFAULT_PWM_RANGE)


class MotorController(Component):
  def __init__(self):
    self.pi = pigpio.pi()
    if not self.pi.connected:
      raise RuntimeError("Could not connect to pigpio daemon. Start it with: sudo systemctl enable --now pigpiod")
    
    # left
    self.ENA = _board_to_bcm(config.PIN_ENA)
    self.IN1 = _board_to_bcm(config.PIN_IN1) #forward
    self.IN2 = _board_to_bcm(config.PIN_IN2) #backward

    # right
    self.ENB = _board_to_bcm(config.PIN_ENB)
    self.IN3 = _board_to_bcm(config.PIN_IN3) #forward
    self.IN4 = _board_to_bcm(config.PIN_IN4) #backward

    for pin in self.ENA, self.IN1, self.IN2, self.ENB, self.IN3, self.IN4:
      self.pi.set_mode(pin, pigpio.OUTPUT)

    for pin in self.IN1, self.IN2, self.IN3, self.IN4:
      self.pi.write(pin, 0)

    self._configure_pwm(self.ENA)
    self._configure_pwm(self.ENB)
    self._cleaned_up = False

  def _configure_pwm(self, pin: int) -> None:
    self.pi.set_PWM_frequency(pin, DEFAULT_PWM_HZ)
    self.pi.set_PWM_range(pin, DEFAULT_PWM_RANGE)
    self.pi.set_PWM_dutycycle(pin, 0)

  def execute(self, cmd: MotorCommand) -> None:
    speed = _clamp(cmd.speed_val, 0.0, 1.0)
    turning = _clamp(cmd.turning_val, -1.0, 1.0)

    # left = LEFT_MAX_DUTY * speed
    # right = RIGHT_MAX_DUTY * speed

    # motors are failing to scale from 0-100, set at perm low
    left = LEFT_MAX_DUTY if speed > 0.0 else 0.0
    right = RIGHT_MAX_DUTY if speed > 0.0 else 0.0

    if turning > 0:
      right *= 1 - (2 * turning)
    elif turning < 0:
      left *= 1 + (2 * turning)

    self._set_motor(self.ENA, self.IN1, self.IN2, left)
    self._set_motor(self.ENB, self.IN3, self.IN4, right)

  def _set_motor(self, pwm_pin, forward_pin, backward_pin, duty) -> None:
    duty = _clamp(duty, -100.0, 100.0)

    if duty > 0:
      self.pi.write(forward_pin, 1)
      self.pi.write(backward_pin, 0)
    elif duty < 0:
      self.pi.write(forward_pin, 0)
      self.pi.write(backward_pin, 1)
    else:
      self.pi.write(forward_pin, 0)
      self.pi.write(backward_pin, 0)

    self.pi.set_PWM_dutycycle(pwm_pin, _duty_percent_to_pwm(duty))

  def cleanup(self) -> None:
    if self._cleaned_up:
      return

    try:
      self.execute(MotorCommand(turning_val=0.0, speed_val=0.0))
    finally:
      self.pi.stop()
      self._cleaned_up = True
