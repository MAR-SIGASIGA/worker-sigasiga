import time
import cv2
import multiprocessing
import pickle
import av
import redis
import os
from .redis_stream_reader import RedisStreamReader
import setproctitle
import numpy as np

class ClientFramesProcessor(multiprocessing.Process):
    def __init__(self, redis_client, event_id, client_id, name=None):
        super().__init__(name=name)
        self.redis_client = redis_client
        self.event_id = event_id
        self.client_id = client_id

    def webm_reader(self):
        """
        Este método se encarga de leer el stream de video desde Redis y guardarlo en Redis como PNG y WEBP.
        Template de claves IMPORTANTES referidas al evento y cliente:
        - {event_id}-chunks_data_input_buffer-{client_id}
        - {event_id}-video_source-{client_id}
        - {event_id}-video_source_thumbnail-{client_id}
        - {event_id}-video_source-{client_id}-process_alive
        - {event_id}-video_source_orientation-{client_id}
        """
        # === GUARDAR ORIGINAL EN PNG (alta calidad) ===
        chunk_buffer_redis_key = f"{self.event_id}-chunks_data_input_buffer-{self.client_id}"
        # Crear el lector de stream desde Redis
        stream_reader = RedisStreamReader(self.redis_client, chunk_buffer_redis_key)
        print(f"🟢 Iniciando lectura del stream desde Redis key: {chunk_buffer_redis_key}")
        redis_video_source_key = f"{self.event_id}-video_source-{self.client_id}"
        redis_thumnail_video_source_key = f"{self.event_id}-video_source_thumbnail-{self.client_id}"

        try:
            # Abrir el contenedor con PyAV desde nuestro lector
            container = av.open(stream_reader, format='webm')
            one_second_png_frames_size = 0
            one_second_webp_frames_size = 0
            frames_process_time = 0
            previous_time = time.time()
            previous_frame_timestamp = 0
            exceeds_time = 0
            frame_count = 0
            exceed_wait_time_frame_count = 0
            process_time_start = time.time()
            for packet in container.demux(video=0):  # demux solo video
                process_alive = int(self.redis_client.get(f"{self.event_id}-video_source-{self.client_id}-process_alive"))
                if not process_alive:
                    print("🛑 Proceso detenido por el cliente")
                    os._exit(0)
                    break
                for frame in packet.decode():
                    if frame.pts is not None:
                        frame_timestamp = frame.pts * frame.time_base
                    img = frame.to_ndarray(format='bgr24')
                    #Obtener resolucion del frame original, ancho y alto
                    # height, width = img.shape[:2]
                    # print(f"🟢 Resolucion del frame original (ancho x alto): {width}x{height}")
                    #Obtener resolucion del frame original, ancho y alto
                    final_frame = self.resize_and_center_frame_on_canvas(img)
                    # === GUARDAR ORIGINAL EN PNG (alta calidad) ===
                    png_orig = cv2.imencode('.png', final_frame)[1].tobytes()
                    self.redis_client.set(redis_video_source_key, png_orig)
                    one_second_png_frames_size += len(png_orig) / 1024  # 1 KB = 1024 bytes
                    # print(f"🟢 Frame {frame.pts} procesado y guardado en Redis key: {redis_key} | Tamaño: {frame_size_kb:.2f} KB")

                    # === REDIMENSIONAR Y GUARDAR COMPRIMIDA (640x360, calidad 30) ===
                    resized_img = cv2.resize(final_frame, (640, 360), interpolation=cv2.INTER_AREA)
                    encode_params_comp = [int(cv2.IMWRITE_WEBP_QUALITY), 10]
                    webp_comp = cv2.imencode('.webp', resized_img, encode_params_comp)[1].tobytes()
                    self.redis_client.set(redis_thumnail_video_source_key, webp_comp)
                    one_second_webp_frames_size += len(webp_comp) / 1024  # 1 KB = 1024 bytes
                    # print(f"🟢 Thumbnail {frame.pts} procesado y guardado en Redis key: {redis_key} | Tamaño: {frame_size_kb:.2f} KB")

                    if time.time() - previous_time >= 1:
                        # print(f"📊 Estadísticas del cliente {self.client_id} en el último segundo:")
                        # print(f"\t🎞️ Frames procesados en el último segundo: {frame_count}")
                        # print(f"\t💾 Tamaño promedio de frames PNG: {one_second_png_frames_size / frame_count:.2f} KB")
                        # print(f"\t💾 Tamaño promedio de frames WEBP: {one_second_webp_frames_size / frame_count:.2f} KB")
                        # print(f"\t📤 Bandwidth por segundo PNG: {one_second_png_frames_size:.2f} KB")
                        # print(f"\t📤 Bandwidth por segundo WEBP: {one_second_webp_frames_size:.2f} KB")
                        # print(f"\t⏳ Tiempo promedio de procesamiento por frame: {frames_process_time / frame_count:.4f} segundos")
                        # print(f"\t⏳ Frames excedidos de tiempo de espera: {exceed_wait_time_frame_count}")

                        one_second_png_frames_size = 0
                        one_second_webp_frames_size = 0
                        frames_process_time = 0
                        frame_count = 0
                        exceed_wait_time_frame_count = 0
                        previous_time = process_time_end

                    frame_count += 1
                    process_time_end = time.time()
                    frame_process_time = process_time_end - process_time_start
                    frames_process_time += frame_process_time
                    frame_wait_time = frame_timestamp - previous_frame_timestamp
                    wait_time = frame_wait_time - frame_process_time - exceeds_time
                    previous_frame_timestamp = frame_timestamp


                    if wait_time > 0:
                        time.sleep(wait_time)
                        exceeds_time = 0
                    else:
                        exceed_wait_time_frame_count += 1
                        exceeds_time = abs(wait_time)

                    process_time_start = time.time()

        except Exception as e:
            print(f"❌ Error durante lectura/decodificación: {e}")
        finally:
            stream_reader.close()
            print("🟢 Lectura finalizada")

    def resize_and_center_frame_on_canvas(self, img, canvas_width=1280, canvas_height=720):
        orientation = int(self.redis_client.get(f"{self.event_id}-video_source_orientation-{self.client_id}"))
        if orientation == 0:
            img = img
        elif orientation == 1:
            img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        elif orientation == 2:
            img = cv2.rotate(img, cv2.ROTATE_180)
        elif orientation == 3:
            img = cv2.rotate(img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        else:
            img = img


        original_height, original_width = img.shape[:2]

        if original_height > original_width:
            scale = canvas_height / original_height
            new_height = canvas_height
            new_width = int(original_width * scale)
        else:
            scale = canvas_width / original_width
            new_width = canvas_width
            new_height = int(original_height * scale)

        resized_img = cv2.resize(img, (new_width, new_height), interpolation=cv2.INTER_AREA)
        canvas = np.zeros((canvas_height, canvas_width, 3), dtype=np.uint8)

        x_offset = (canvas_width - new_width) // 2
        y_offset = (canvas_height - new_height) // 2

        canvas[y_offset:y_offset+new_height, x_offset:x_offset+new_width] = resized_img

        return canvas

    def run(self):
        setproctitle.setproctitle(f"{self.event_id}-cfp-{self.client_id}")
        print(f"client frame processor for event {self.event_id} and client {self.client_id}")
        self.redis_client.set(f"{self.event_id}-video_source-{self.client_id}-process_alive", int(True))
        self.redis_client.set(f"{self.event_id}-video_source_orientation-{self.client_id}", int(0))
        self.webm_reader()


