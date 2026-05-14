from core.types import Component, MotorCommand

import Jetson.GPIO as GPIO 

class MotorController(Component):
  def __init__(self):
    GPIO.setmode(GPIO.BOARD) #gonna make us use board mode for now, lmk if no
    
    inputChannels = [] #put pin numbers here, but we don't know them yet so
    outputChannels = []
    
    GPIO.setup(inputChannels, GPIO.IN)
    GPIO.setup(outputChannels, GPIO.OUT)

  
  def execute(self, cmd: MotorCommand) -> None:
    #here i am taking the info from motorcommand and putting stuff into the pins
    #turning_val and speed_val
    #help
    pass

  def cleanup(self) -> None:
    GPIO.cleanup()
