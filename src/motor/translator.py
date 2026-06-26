from core.types import Component, CameraData, StateRules, MotorCommand
import config


def _clamp(value: float, low: float, high: float) -> float:
  return max(low, min(high, value))


class MotorTranslator(Component):
  def __init__(self):
    pass

  def compute(self, perception: CameraData, rules: StateRules) -> MotorCommand:
    speed_val = _clamp(rules.speed_lim, 0.0, 1.0)

    if perception.arrow is not None and not rules.ignore_arrows:
      turning_val = perception.arrow * rules.turning_lim
    else:
      turning_val = (perception.turning - 0.5) * 2 * config.MOTOR_TURN_GAIN

    turning_limit = _clamp(rules.turning_lim, 0.0, 1.0)
    turning_val = _clamp(turning_val, -turning_limit, turning_limit)

    return MotorCommand(
      turning_val=turning_val,
      speed_val=speed_val,
    )

  def cleanup(self) -> None:
    pass
