import time
import redis
import cv2
import numpy as np
from multiprocessing import Process

class FramePlayer(Process):
    def __init__(self, event_id, redis_client):
        super().__init__()
        self.event_id = event_id
        self.redis_client = redis_client
        self.fps = 25
        self.frame_time = 1.0 / self.fps

    def run(self):
        """Main process loop to display frames."""
        window_name = "Scoreboard Display"
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

        while True:
            start_time = time.time()
            # Read PNG data from Redis
            png_bytes = self.redis_client.get(f"{self.event_id}-scoreboard_frame")
            if png_bytes:
                # Convert PNG bytes to numpy array
                nparr = np.frombuffer(png_bytes, np.uint8)
                frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                cv2.imshow(window_name, frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            # Calculate sleep time to maintain FPS
            elapsed = time.time() - start_time
            sleep_time = max(0, self.frame_time - elapsed)
            time.sleep(sleep_time)
        cv2.destroyAllWindows()

if __name__ == "__main__":
    event_id = input("Enter event ID: ")
    frame_player = FramePlayer(event_id, redis.Redis(host='localhost', port=31802, db=0))
    frame_player.start()
    frame_player.join()