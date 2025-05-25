import time
import redis
from multiprocessing import Process
import setproctitle
from .sio_pubsub_redis import publish_to_redis

class EventTimer(Process):
    def __init__(self, event_id, redis_client):
        super().__init__()
        self.event_id = event_id
        self.redis_client = redis_client
        self.timer_key = f"{self.event_id}-scoreboard-timer"
        self.status_key = f"{self.event_id}-scoreboard-timer_status"

    def read_timer_status(self):
        """Read the current timer status from Redis."""
        status = self.redis_client.get(self.status_key)
        if status is not None:
            return int(status) == 1
        return False

    def update_timer_status(self, status):
        """Update the timer status in Redis."""
        self.redis_client.set(self.status_key, 1 if status else 0)

    def read_timer_value(self):
        """Read the current timer value from Redis."""
        value = self.redis_client.get(self.timer_key)
        if value is not None:
            return int(value)
        return 0

    def update_timer(self, new_value):
        """Update the timer value in Redis."""
        self.redis_client.set(self.timer_key, new_value)

    def publish_scoreboard_data(self):
        """Publish the scoreboard data to Redis."""
        scoreboard_data = {
            "local_team": self.redis_client.get(f"{self.event_id}-scoreboard-local_team").decode("utf-8"),
            "visitor_team": self.redis_client.get(f"{self.event_id}-scoreboard-visitor_team").decode("utf-8"),
            "local_points": self.redis_client.get(f"{self.event_id}-scoreboard-local_points").decode("utf-8"),
            "visitor_points": self.redis_client.get(f"{self.event_id}-scoreboard-visitor_points").decode("utf-8"),
            "period": self.redis_client.get(f"{self.event_id}-scoreboard-period").decode("utf-8"),
            "timer": self.redis_client.get(f"{self.event_id}-scoreboard-timer").decode("utf-8"),
            "timer_status": bool(int(self.redis_client.get(f"{self.event_id}-scoreboard-timer_status").decode("utf-8"))),
            "24_timer": self.redis_client.get(f"{self.event_id}-scoreboard-24_timer").decode("utf-8"),
            "24_timer_status": bool(int(self.redis_client.get(f"{self.event_id}-scoreboard-24_timer_status").decode("utf-8"))),
            "visible": bool(int(self.redis_client.get(f"{self.event_id}-scoreboard-visible").decode("utf-8")))
        }
        print("timer_status: ", scoreboard_data["timer_status"])
        publish_to_redis(redis_client=self.redis_client, 
                    event_id=self.event_id, event_type="scoreboard_room", data_dict=scoreboard_data)

    def run(self):
        """Main timer process loop."""
        setproctitle.setproctitle(f"{self.event_id}-scoreboard_timer")
        while True:
            if self.read_timer_status():
                current_time = self.read_timer_value()
                if current_time > 0:
                    new_time = max(0, current_time - 100)
                    self.update_timer(new_time)
                else:
                    self.update_timer_status(False)
            self.publish_scoreboard_data()
            time.sleep(0.1)