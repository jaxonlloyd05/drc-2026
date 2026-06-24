#!/usr/bin/env python3

from core.state_machine import StateMachine
from perception.camera import Camera
from perception.output import CameraDisplay
from motor.translator import MotorTranslator
# from motor.controller import MotorController

def main() -> None:
  components = [
    Camera(),
    StateMachine(),
    MotorTranslator(),
    # MotorController(),
    CameraDisplay()
  ]

  camera, state_machine, translator, display = components

  try:
    camera.start()

    while True:
      perception = camera.read()
      rules, state = state_machine.update(perception)
      command = translator.compute(perception, rules)
      print(command)
      # controller.execute(command)
      display.show(perception, state)

  except KeyboardInterrupt:
    print('\n\n[EXIT] Putting robot to sleep...')

  finally:
    for i in components:
      i.cleanup()


if __name__ == '__main__':
  main()
