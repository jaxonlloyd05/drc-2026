from core.types import Component, MotorCommand
from enum import Enum

import Jetson.GPIO as GPIO

class StupidEnum (Enum):
  LEFT_FW = (True, False, None, None)
  LEFT_BW = (False, True, None, None)
  RIGHT_FW = (None, None, True, False)
  RIGHT_BW = (None, None, False, True)

class MotorController(Component):
  def __init__(self):
    GPIO.setmode(GPIO.BOARD) #gonna make us use board mode for now, lmk if no
    #left
    self.ENA = 32 
    self.IN1 = 22 #forward
    self.IN2 = 24 #backward
    
    #right
    self.ENB = 33
    self.IN3 = 21 #forward
    self.IN4 = 23 #backward

    for pin in self.ENA, self.IN1, self.IN2, self.ENB, self.IN3, self.IN4:
      GPIO.setup(pin, GPIO.OUT)

  def change_fb(self, opt: StupidEnum):
    ins = [
      (self.IN1, opt[0]),
      (self.IN2, opt[1]),
      (self.IN3, opt[2]),
      (self.IN4, opt[3])
    ]

    for i in ins:
      if i[1] is not None:
        GPIO.output(i[0], GPIO.HIGH if i[1] else GPIO.LOW)

  


  # def thunk(self, cmd: MotorCommand):
  #   turning = cmd.turning_val/180 #how should I scale it to make sense 
  #   offset = cmd.offset

  #   forward = True
  #   speed = cmd.speed_val 

  #   if (speed < 0):
  #     speed = -speed
  #     forward = False


  #   rightTurn = speed - turning 
  #   leftTurn = speed + turning

  #   #scale to largest out of rightturn, leftturn or 1
  #   scale = max(rightTurn, leftTurn, 1)

  #   return [(rightTurn/scale)*100, (leftTurn/scale)*100] #help idk
    
    
  
  def execute(self, cmd: MotorCommand) -> None:
    #here i am taking the info from motorcommand and putting stuff into the pins
    #turning_val and speed_val
    #help
    directions = self.thunk(cmd)



    pass

  def cleanup(self) -> None:
    GPIO.cleanup()
