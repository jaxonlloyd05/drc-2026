from core.types import Component, CameraData, State
import cv2

class CameraDisplay(Component):
  def __init__(self):
    pass

  def show(self, data: CameraData, state: State) -> None:    
    cv2.imshow(state.value, data.frame)
    cv2.waitKey(1)
  
  def cleanup(self) -> None:
    cv2.destroyAllWindows()
    pass