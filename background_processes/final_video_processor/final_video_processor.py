import multiprocessing
from PIL import Image
import redis
import time
import io
import os
import setproctitle
#TODO: optimizar
class FinalVideoProcessor(multiprocessing.Process):
    """
    Final Video Processor class to handle video processing tasks.
    """
    def __init__(self, redis_client, event_id, name=None):
        super().__init__(name=name)
        self.redis_client = redis_client
        self.event_id = event_id
    #TODO: Optimizar el procesamiento de frames y comprimir default frame en origen
    def process_video_frames(self):
        """
        Este método se encarga de leer el stream de video desde Redis y guardarlo en Redis como PNG y WEBP.
        Template de claves IMPORTANTES referidas al evento, a la fuente de video seleccionada, al scoreboard y al frame final.
        - {event_id}-video_source-final_frame
        - {event_id}-video_source_thumbnail-final_frame
        - {event_id}-scoreboard_frame
        - {event_id}-selected_source ---> Clave que CONTIENE la clave de la fuente de video seleccionada. Para obtener el frame de la fuente de video seleccionada, 
            se debe obtener el valor de esta clave y usarlo como clave para obtener el frame de la fuente de video seleccionada.
        - {event_id}-scoreboard-visible ---> Contiene el estado del scoreboard.
        """

        current_path = os.path.dirname(os.path.abspath(__file__))
        default_frame_path = os.path.join(current_path, "resources", "default.webp")
        thumbnail_default_frame_path = os.path.join(current_path, "resources", "thumbnail_default.webp")
        # print(f"Default frame path: {default_frame_path}")
        frame_rate = 30
        final_video_frame_key = f"{self.event_id}-video_source-final_frame"
        final_video_thumbnail_key = f"{self.event_id}-video_source_thumbnail-final_frame"
        scoreboard_frame_key = f"{self.event_id}-scoreboard_frame"
        default_frame = Image.open(default_frame_path)
        default_frame = default_frame.convert("RGBA")

        default_video_source_key = f"{self.event_id}-video_source-default"
        thumbnail_default_video_source_key = f"{self.event_id}-video_source_thumbnail-default"

        buffer = io.BytesIO()
        default_frame.save(buffer, format="WEBP")
        default_webp_bytes = buffer.getvalue()

        thumbnail_default_file = open(thumbnail_default_frame_path, "rb")
        thumbnail_default_webp_bytes = thumbnail_default_file.read()
        thumbnail_default_file.close()

        self.redis_client.set(default_video_source_key, default_webp_bytes)
        self.redis_client.set(thumbnail_default_video_source_key, thumbnail_default_webp_bytes)

        name_selected_source_key = f"{self.event_id}-selected_source"
        name_selected_source = "default"
        self.redis_client.set(name_selected_source_key, name_selected_source.encode('utf-8'))
        time.sleep(2)
        frames_per_second_size = 0
        frames_count = 0
        while True:
            start_time = time.time()
            selected_source_key = f"{self.event_id}-video_source-" + self.redis_client.get(name_selected_source_key).decode('utf-8')
            frame_to_process = self.redis_client.get(selected_source_key)
            frame_to_process = Image.open(io.BytesIO(frame_to_process)) if frame_to_process is not None else None
            bytes_scoreboard_frame = self.redis_client.get(scoreboard_frame_key)
            scoreboard_frame = Image.open(io.BytesIO(bytes_scoreboard_frame))
            scoreboard_frame = scoreboard_frame.convert("RGBA")
            frame_to_process.paste(scoreboard_frame, (0, 0), scoreboard_frame)
            if frame_to_process is not None:
                try:
                    buffer = io.BytesIO()
                    frame_to_process_original = frame_to_process.convert("RGB")
                    frame_to_process_original.save(buffer, format="WEBP", quality=70)
                    frame_to_process_bytes = buffer.getvalue()
                    frames_per_second_size += len(frame_to_process_bytes)
                    frames_count += 1
                    self.redis_client.set(final_video_frame_key, frame_to_process_bytes)

                    buffer = io.BytesIO()
                    frame_to_process_original.save(buffer, format="WEBP", quality=3)
                    frame_to_process_thumbnail_bytes = buffer.getvalue()
                    self.redis_client.set(final_video_thumbnail_key, frame_to_process_thumbnail_bytes)
                except Exception as e:
                    self.redis_client.set(final_video_frame_key, default_webp_bytes)
                    self.redis_client.set(final_video_thumbnail_key, default_webp_bytes)
            else:
                self.redis_client.set(final_video_frame_key, default_webp_bytes)
                self.redis_client.set(final_video_thumbnail_key, default_webp_bytes)
            end_time = time.time()
            elapsed_time = end_time - start_time
            wait_time = (1 / frame_rate) - elapsed_time
            if wait_time > 0:
                time.sleep(wait_time)
            if frames_count >= 30:
                frames_count = 0
                # avg_frames_size = frames_per_second_size / 30 / 1024
                # print(f"Tamaño total 30fps: {frames_per_second_size/1024:.2f} KB, Tamaño promedio: {avg_frames_size:.2f} KB")
                frames_per_second_size = 0

    def run(self):
        setproctitle.setproctitle(f"{self.event_id}-final_video")
        print(f"Final video processor started for event {self.event_id}")
        self.process_video_frames()
        print(f"Final video processor stopped for event {self.event_id}")

if __name__ == "__main__":
    redis_client = redis.Redis(host='localhost', port=31802, db=0)
    event_id = "test_id"
    print(f"Event ID: {event_id}")
    final_video_processor = FinalVideoProcessor(redis_client, event_id)
    final_video_processor.start()
    final_video_processor.join()
