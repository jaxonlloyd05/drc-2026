from core.types import Component, MotorCommand

import RPi.GPIO as GPIO 
import config

DEFAULT_PWM_HZ = 1000
LEFT_MAX_DUTY = 90.0
RIGHT_MAX_DUTY = 95.0


def _clamp(value: float, low: float, high: float) -> float:
  return max(low, min(high, value))


class MotorController(Component):
  def __init__(self):
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)

    self.ENA = config.PIN_ENA

    # left
    self.IN1 = config.PIN_IN1 #forward
    self.IN2 = config.PIN_IN2 #backward

    #right
    self.ENB = config.PIN_ENB
    self.IN3 = config.PIN_IN3 #forward
    self.IN4 = config.PIN_IN4 #backward

    for pin in self.ENA, self.IN1, self.IN2, self.ENB, self.IN3, self.IN4:
      GPIO.setup(pin, GPIO.OUT)

    for pin in self.IN1, self.IN2, self.IN3, self.IN4:
      GPIO.output(pin, GPIO.LOW)

    self.left_pwm = GPIO.PWM(self.ENA, DEFAULT_PWM_HZ)
    self.right_pwm = GPIO.PWM(self.ENB, DEFAULT_PWM_HZ)
    self.left_pwm.start(0)
    self.right_pwm.start(0)
    self._cleaned_up = False

  def execute(self, cmd: MotorCommand) -> None:
    speed = _clamp(cmd.speed_val, 0.0, 1.0)
    turning = _clamp(cmd.turning_val, -1.0, 1.0)

    # left = LEFT_MAX_DUTY * speed
    # right = RIGHT_MAX_DUTY * speed

    # motors are failing to scale from 0-100, set at perm low
    left = LEFT_MAX_DUTY
    right = RIGHT_MAX_DUTY

    if turning > 0:
      right *= 1 - (2 * turning)
    elif turning < 0:
      left *= 1 + (2 * turning)

    self._set_motor(self.left_pwm, self.IN1, self.IN2, left)
    self._set_motor(self.right_pwm, self.IN3, self.IN4, right)

  def _set_motor(self, pwm: GPIO.PWM, forward_pin: int, backward_pin: int, duty: float) -> None:
    duty = _clamp(duty, -100.0, 100.0)

    if duty > 0:
      GPIO.output(forward_pin, GPIO.HIGH)
      GPIO.output(backward_pin, GPIO.LOW)
    elif duty < 0:
      GPIO.output(forward_pin, GPIO.LOW)
      GPIO.output(backward_pin, GPIO.HIGH)
    else:
      GPIO.output(forward_pin, GPIO.LOW)
      GPIO.output(backward_pin, GPIO.LOW)

    pwm.ChangeDutyCycle(abs(duty))

  def cleanup(self) -> None:
    if self._cleaned_up:
      return

    try:
      self.execute(MotorCommand(turning_val=0.0, speed_val=0.0))
      self.left_pwm.stop()
      self.right_pwm.stop()
    finally:
      GPIO.cleanup()
      self._cleaned_up = True
