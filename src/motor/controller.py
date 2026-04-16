from core.types import Component, MotorCommand
# import Jetson.GPIO as GPIO

class MotorController(Component):
  def __init__(self):
    pass

  def execute(self, cmd: MotorCommand) -> None:
    pass

  def cleanup(self) -> None:
    pass