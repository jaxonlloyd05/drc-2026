from core.types import Transition, State, StateRules, CameraData, Component


class StateMachine(Component):
  def __init__(self):
    self.state = State.STOPPED
    self.transitions = _build_transitions()
    self.rules = _build_rules()

  def update(self, perceptions: CameraData) -> tuple[StateRules, State]:
    for i in self.transitions:
      if None in i.from_state or self.state in i.from_state:
        if i.condition(perceptions):
          self.state = i.to_state
          break
    
    return self.rules[self.state], self.state
  
  def cleanup(self) -> None:
    pass



def _build_transitions() -> list[Transition]:
  # THESE ARE ORDERED BY PRIORITY, IF YOU CHANGE THEM MAKE SURE THE MOST IMPORTANT ARE UP THE TOP
  # havent added obstacles yet, have to decide how it will be done (i.e. obj det or depth perc)
  return [
    Transition([State.STOPPED],                             State.CONTROLLER,     lambda x: x.controller is True),
    Transition([None],                                      State.STOPPED,        lambda x: x.stop is True),
    Transition([None],                                      State.LOST,           lambda x: x.confidence < 0.2),
    Transition([None],                                      State.TURNING,        lambda x: 0.35 <= x.turning <= 0.65),
    Transition([State.TURNING],                             State.TURNING_ARROW,  lambda x: x.arrow is not None), 
    Transition([State.CERTAIN, State.STOPPED, State.LOST],  State.UNCERTAIN,      lambda x: x.confidence < 0.5), 
    Transition([State.UNCERTAIN, State.TURNING],            State.CERTAIN,        lambda x: x.confidence > 0.7),
    Transition([None],                                      State.LOST,           lambda x: x.stop is False)
  ]

def _build_rules() -> dict[State, StateRules]:
  return {
    State.STOPPED: StateRules(
      speed_lim=0.0,
      turning_lim=0,
      obstacle_lim=0.0,
      ignore_arrows=True,
    ),
    State.LOST: StateRules(
      speed_lim=0.3,
      turning_lim=1,
      obstacle_lim=0.2,
      ignore_arrows=True,
    ),
    State.TURNING: StateRules(
      speed_lim=0.5,
      turning_lim=1,
      obstacle_lim=1,
      ignore_arrows=False
    ),
    State.TURNING_ARROW: StateRules(
      speed_lim=0.5,
      turning_lim=1,
      obstacle_lim=1,
      ignore_arrows=False
    ),
    State.CERTAIN: StateRules(
      speed_lim=1,
      turning_lim=0.3,
      obstacle_lim=0.3,
      ignore_arrows=False
    ),
    State.UNCERTAIN: StateRules(
      speed_lim=0.6,
      turning_lim=0.6,
      obstacle_lim=0.6,
      ignore_arrows=False
    ),
    State.CONTROLLER: StateRules(
      speed_lim=1.0,
      turning_lim=1.0,
      obstacle_lim=0.0,
      ignore_arrows=True
    )
  }