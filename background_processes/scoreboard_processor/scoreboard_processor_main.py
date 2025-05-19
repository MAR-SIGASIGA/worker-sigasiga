import os
import sys
import redis
import shortuuid
import multiprocessing
from .scoreboard_frame_processor import ScoreboardFrameProcessor
from .secoreboard_event_timer import EventTimer
import time
import setproctitle

class ScoreboardProcess(multiprocessing.Process):
    def __init__(self, event_id, redis_client):
        super().__init__()
        self.event_id = event_id
        self.redis_client = redis_client

    def initialize_redis_keys(self):
        """Initialize default Redis keys for the scoreboard."""
        default_keys = {
            f"{self.event_id}-scoreboard-local_team": "BOCA",
            f"{self.event_id}-scoreboard-visitor_team": "RIVER",
            f"{self.event_id}-scoreboard-local_points": 0,
            f"{self.event_id}-scoreboard-visitor_points": 0,
            f"{self.event_id}-scoreboard-period": 1,
            f"{self.event_id}-scoreboard-timer": 10 * 60 * 1000,
            f"{self.event_id}-scoreboard-timer_status": 0,
            f"{self.event_id}-scoreboard-24_timer": 24 * 1000,
            f"{self.event_id}-scoreboard-24_timer_status": 0,
    }

        for key, value in default_keys.items():
            self.redis_client.set(key, value)

    def run(self):
        """Main process loop."""
        setproctitle.setproctitle(f"{self.event_id}-scoreboard_main")
        # Initialize Redis keys
        self.initialize_redis_keys()
        frame_processor = ScoreboardFrameProcessor(event_id=self.event_id, redis_client=self.redis_client, name=f"{self.event_id}-scoreboard_frames")
        timer = EventTimer(self.event_id, self.redis_client)
        frame_processor.start()
        timer.start()
        try:
            while True:
                time.sleep(1)
        except Exception as e:
            print(f"❌ Error in scoreboard process: {e}")
        finally:
            print("\nShutting down processes...")
            frame_processor.terminate()
            timer.terminate()
            frame_processor.join()
            timer.join()
            print("All processes terminated.")

if __name__ == "__main__":
    redis_client = redis.Redis(host='localhost', port=31802, db=0)
    event_id = "test_id"
    print(f"Event ID: {event_id}")
    scoreboard_process = ScoreboardProcess(event_id, redis_client)
    scoreboard_process.start()
    scoreboard_process.join()


