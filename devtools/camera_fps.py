import cv2
import time

cap = cv2.VideoCapture(0)
prev_time = 0
fps = 0

while True:
    success, frame = cap.read()
    if not success:
      print("Failed to grab frame.")
      break
    
    current_time = time.perf_counter()
    time_diff = current_time - prev_time
    prev_time = current_time

    if time_diff > 0:
      fps = int(1 / time_diff)

    fps_text = f"FPS: {fps}"
    cv2.putText(frame, fps_text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.imshow("Live Camera Stream", frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
      break

cap.release()
cv2.destroyAllWindows()
