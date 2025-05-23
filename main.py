import redis
import multiprocessing
import importlib
import os
import signal
import sys
import json
from background_processes import (ClientFramesProcessor, FinalVideoProcessor, 
                                  ScoreboardProcess, ThumbnailsSioPubFeeder,
                                  RtmpEmitter)
import setproctitle

# from dotenv import load_dotenv

# # Load environment variables
# load_dotenv()

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', 'redis-sigasiga')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
REDIS_DB = int(os.getenv('REDIS_DB', 0))

class EventManager(multiprocessing.Process):
    def __init__(self, event_id):
        super().__init__(name=f"{event_id}-manager")
        self.event_id = event_id
        self.processes = []
        self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
        self.pubsub = self.redis_client.pubsub()
        self.pubsub.subscribe(f"{event_id}-event_manager")

    def load_background_processes(self):
        """Load and start all background processes from the modules directory"""
        # Load the scoreboard process
        scoreboard_process = ScoreboardProcess(self.event_id, self.redis_client)
        scoreboard_process.start()
        self.processes.append(scoreboard_process)
        # Load the final video processor
        final_video_processor = FinalVideoProcessor(self.redis_client, self.event_id, name=f"{self.event_id}-final_video")
        final_video_processor.start()
        self.processes.append(final_video_processor)
        # Load the thumbnails socket.io feeder
        thumbnails_sio_pub_feeder = ThumbnailsSioPubFeeder(self.redis_client, self.event_id, name=f"{self.event_id}-thumbs_feeder")
        thumbnails_sio_pub_feeder.start()
        self.processes.append(thumbnails_sio_pub_feeder)


    def handle_actions(self):
        """Handle actions received through Redis pub/sub
            Actions include:
            - stop_event: Stop all background processes. No data is sent.
            - new_client: Start a new client process. Data is sent with the following structure:
                {
                    "action": "new_client",
                    "data": {
                        "client_id": <client_id>
                    }
                }
        """
        for message in self.pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(str(message['data'].decode('utf-8')))
                action = data.get('action')
                if action == 'stop_event':
                    self.stop_all_processes()
                    return
                if action == 'new_client':
                    data = data.get('data')
                    client_id = data.get('client_id')

                    client_frames_process = ClientFramesProcessor(
                        redis_client=self.redis_client,
                        event_id=self.event_id,
                        client_id=client_id,
                        name=f"{self.event_id}-cfp-{client_id}"
                    )
                    client_frames_process.start()
                    self.processes.append(client_frames_process)
                if action == 'start_rtmp_emitter':
                    try:
                        rtmp_url_base = self.redis_client.get(f"{self.event_id}-rtmp_url").decode('utf-8')
                        rtmp_key = self.redis_client.get(f"{self.event_id}-rtmp_key").decode('utf-8')
                        rtmp_url = f"{rtmp_url_base}/{rtmp_key}"
                        rtmp_emitter = RtmpEmitter(redis_client=self.redis_client, event_id=self.event_id, rtmp_url=rtmp_url)
                        rtmp_emitter.start()
                        self.processes.append(rtmp_emitter)
                        
                    except Exception as e:
                        print(f"Error starting RTMP emitter: {str(e)}")

    def stop_all_processes(self):
        """Stop all background processes"""
        for process in self.processes:
            try:
                if process.is_alive():
                    process.terminate()
                    process.join()
            except Exception as e:
                print(f"Error stopping process: {str(e)}")
        print(f"All processes for event {self.event_id} have been stopped")
        os._exit(0)

    def run(self):
        """Main loop for the event manager"""
        setproctitle.setproctitle(f"{self.event_id}-event_manager")
        print(f"Event manager started for event {self.event_id}")
        self.load_background_processes()
        self.handle_actions()
        print(f"Event manager stopped for event {self.event_id}")


def main():
    redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)
    event_managers = {}

    def signal_handler(sig, frame):
        print("\nShutting down gracefully...")
        # Stop all event managers
        for event_id, process in event_managers.items():
            try:
                if process.is_alive():
                    redis_client.publish(f"{event_id}-event-manager", "stop_event")
                    process.join()
            except Exception as e:
                print("Error: ", str(e))

        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("Listening for events...")
    while True:
        try:
            print("Waiting for event..")
            result = redis_client.blpop('start_event', timeout=0)
            if result is None:
                continue

            _, event_id = result
            event_id = event_id.decode('utf-8')
            print(f"Received event ID: {event_id}")

            # Check if event manager for this event already exists
            if event_id in event_managers and event_managers[event_id].is_alive():
                print(f"Event manager for {event_id} is already running")
                continue

            # Create new process for the event manager
            process = EventManager(event_id)
            process.start()
            event_managers[event_id] = process
            print(f"Started new event manager process for event {event_id}")

            # Clean up finished processes
            event_managers = {
                event_id: process
                for event_id, process in event_managers.items()
                if process.is_alive()
            }

        except Exception as e:
            print(f"Error processing event: {str(e)}")
            continue

if __name__ == "__main__":
    main()