from core.types import Component, CameraData, State
import cv2

class CameraDisplay(Component):
  def __init__(self):
    pass

  def show(self, data: CameraData, state: State) -> None:
    # testing lines
    cv2.line(data.frame, (0,0), (len(data.frame[0]) // 3, len(data.frame)), (255, 255, 255), 5)
    cv2.line(data.frame, (len(data.frame[0]),0), (len(data.frame[0]) - (len(data.frame[0]) // 3), len(data.frame)), (255, 255, 255), 5)
    cv2.line(data.frame, (len(data.frame[0]) // 2, 0), (len(data.frame[0]) // 2, len(data.frame)), (255, 255, 255), 5)


    cv2.imshow(state.value, data.frame)
    cv2.waitKey(1)
  
  def cleanup(self) -> None:
    cv2.destroyAllWindows()  