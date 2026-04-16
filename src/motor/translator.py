from core.types import Component, CameraData, StateRules, MotorCommand

class MotorTranslator(Component):
  def __init__(self):
    pass

  def compute(self, perception: CameraData, rules: StateRules) -> MotorCommand:
    pass

  def cleanup(self) -> None:
    pass
