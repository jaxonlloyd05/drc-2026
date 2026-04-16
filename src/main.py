from core.state_machine import StateMachine
from perception.camera import Camera
from perception.output import CameraDisplay
from motor.controller import MotorController
from motor.translator import MotorTranslator
# import sys

def main() -> None:
  components = [
    Camera(),
    MotorController(),
    StateMachine(),
    MotorTranslator(),
    CameraDisplay()
  ]

  camera, controller, state_machine, translator, display = components

  try:
    camera.start()

    while True:
      pass
      perc = camera.read()
      rules, state = state_machine.update(perc)
      # command = translator.compute(perc, rules)
      # controller.execute(command)
      display.show(perc, state)

  except KeyboardInterrupt:
    print('\n\n[EXIT] Putting robot to sleep...')

  finally:
    for i in components:
      i.cleanup()


if __name__ == '__main__':
  main()