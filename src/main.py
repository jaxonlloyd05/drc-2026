#!/usr/bin/env python3

from core.state_machine import StateMachine
from perception.camera import Camera
from perception.output import CameraDisplay
from motor.translator import MotorTranslator
from motor.controller import MotorController
from argparse import ArgumentParser
import time

def main() -> None:
  parser = ArgumentParser(description='drc robot params')
  parser.add_argument('headless', type=bool, default=False)

  args = parser.parse_args()

  components = [
    Camera(headless=args.headless),
    StateMachine(),
    MotorTranslator(),
    MotorController(),
    CameraDisplay(headless=args.headless)
  ]

  camera, state_machine, translator, controller, display = components

  try:
    camera.start()
    time.sleep(5)

    while True:
      perception = camera.read()
      rules, _ = state_machine.update(perception)
      command = translator.compute(perception, rules)
      kill_state = controller.execute(command)
      display.show(perception)

      if kill_state:
        return

  except KeyboardInterrupt:
    print('\n\n[EXIT] Putting robot to sleep...')

  finally:
    for i in components:
      i.cleanup()


if __name__ == '__main__':
  main()
