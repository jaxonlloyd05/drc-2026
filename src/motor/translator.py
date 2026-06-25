from core.types import Component, CameraData, StateRules, MotorCommand


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
      turning_val = (perception.turning - 0.5) * 2

    turning_limit = _clamp(rules.turning_lim, 0.0, 1.0)
    turning_val = _clamp(turning_val, -turning_limit, turning_limit)

    # although not the prettiest, we are having hardware issues with motors not recieving enough electricity
    # so im piviting 100% -> -100% and having it move roughly straight
    if turning_val < 0.65 and turning_val > 0.35:
      turning_val = 0.5

    return MotorCommand(
      turning_val=turning_val,
      speed_val=speed_val,
    )

  def cleanup(self) -> None:
    pass
