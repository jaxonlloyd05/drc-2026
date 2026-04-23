from dataclasses import dataclass
import numpy as np
from abc import ABC, abstractmethod
from typing import Callable
from enum import Enum

# components
class Component(ABC):
  @abstractmethod
  def cleanup(self) -> None:
    pass

# enums
class State(Enum):
  CERTAIN = 'CERTAIN'
  UNCERTAIN = 'UNCERTAIN'
  AVOID_OBSTACLE = 'AVOID_OBSTACLE'
  TURNING = 'TURNING'
  TURNING_ARROW = 'TURNING_ARROW',
  LOST = 'LOST'
  STOPPED = 'STOPPED'
  CONTROLLER = 'CONTROLLER'

# dataclasses
@dataclass
class CameraData:
  frame: np.ndarray
  stop: bool
  confidence: float
  turning: float
  arrow: int | None = None  # -1 or 1 (flip turning direction)
  controller: bool = False

@dataclass
class StateRules:
  speed_lim: float    # 0 -> 1
  turning_lim: float  # 0 -> 1
  obstacle_lim: float # 0 -> 1
  ignore_arrows: bool 

@dataclass 
class Transition:
  from_state: State
  to_state: State
  condition: Callable

@dataclass
class MotorCommand:
  turning_val: int  # -1 -> 1
  speed_val: int    # -1 -> 1