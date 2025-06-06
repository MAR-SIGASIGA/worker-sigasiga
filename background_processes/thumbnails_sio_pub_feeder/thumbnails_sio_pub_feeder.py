import multiprocessing
import redis
import time
import pickle
from .redis_list_manager import RedisListManager
import setproctitle

class ThumbnailsSioPubFeeder(multiprocessing.Process):
    """
    SocketIOFeeder class to handle socket.io events and Redis interactions.
    """
    def __init__(self, redis_client, event_id, name=None):
        super().__init__(name=name)
        self.redis_client = redis_client
        self.event_id = event_id

    def run(self):
        setproctitle.setproctitle(f"{self.event_id}-thumbs_feeder")
        base_thumbnail_video_source_key = f"{self.event_id}-video_source_thumbnail-"
        final_video_thumbnail_key = f"{self.event_id}-video_source_thumbnail-final_frame"
        total_data_size = 0
        frames_count = 0
        while True:
            video_source_name_list = RedisListManager(self.redis_client).get_all(f"{self.event_id}-video_sources_list")
            # print(f"available video sources: {str(video_source_name_list)}")
            selected_video_source_name = self.redis_client.get(f"{self.event_id}-selected_source").decode('utf-8')
            # print(f"selected video source: {selected_video_source_name}")
            clients_thumbnails_dict = {}
            thumbnail_key = final_video_thumbnail_key
            thumbnail_data = self.redis_client.get(thumbnail_key)
            total_data_size += len(thumbnail_data) if thumbnail_data else 0
            # if thumbnail_data is not None:
            finalframe_thumbnail_dict = {"frame": thumbnail_data,
                                            "active": selected_video_source_name == "final_frame"}
                # print(f"Thumbnail data for final frame retrieved from Redis.")
            # else:
                # print(f"No thumbnail data found for final frame. Active: {selected_video_source_name == 'final_frame'}")
            for video_source_name in video_source_name_list:
                thumbnail_key = f"{base_thumbnail_video_source_key}{video_source_name}"
                thumbnail_data = self.redis_client.get(thumbnail_key)
                total_data_size += len(thumbnail_data) if thumbnail_data else 0
                # if thumbnail_data is not None:
                clients_thumbnails_dict[video_source_name] = {  "frame": thumbnail_data,
                                                                "active": selected_video_source_name == video_source_name}
                    # print(f"Thumbnail data for {video_source_name} retrieved from Redis.")
                # else:
                    # print(f"No thumbnail data found for {video_source_name}. Active: {selected_video_source_name == video_source_name}")

            # print(f"clients_thumbnails_dict:")
            # print(clients_thumbnails_dict)
            data_dict = {}
            data_dict["finalframe_thumbnail_dict"] = finalframe_thumbnail_dict
            data_dict["clients_thumbnails_dict"] = clients_thumbnails_dict
            final_dict = {
                "event_id": self.event_id,
                "event_type": "director_room",
                "data": data_dict
            }
            self.redis_client.publish("socket_io_data", pickle.dumps(final_dict))
            time.sleep(1/10)
            frames_count += 1
            if frames_count >= 10:
                # print(f"Size total frames to send: {total_data_size/1024:.2f} KB")
                frames_count = 0
                total_data_size = 0

if __name__ == "__main__":
    # Example usage
    redis_client = redis.Redis(host='localhost', port=31802, db=0)
    event_id = "CKGGG3X2JWtSKQZ9pN8DRt"
    feeder = ThumbnailsSioPubFeeder(redis_client, event_id)
    feeder.start()
    feeder.join()