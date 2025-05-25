import pickle
import redis

def publish_to_redis(redis_client, event_id, event_type, data_dict):
    channel = "socket_io_data"
    final_dict = {
    "event_id": event_id,
    "event_type": event_type,
    "data": data_dict
    }
    redis_client.publish(channel, pickle.dumps(final_dict))