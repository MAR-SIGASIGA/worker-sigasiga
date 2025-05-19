import time
import redis
import subprocess
import numpy as np
import cv2
import multiprocessing
class RtmpEmitter(multiprocessing.Process):
    def __init__(self, redis_client, event_id, rtmp_url, fps=25, width=1280, height=720):
        super().__init__()
        self.redis_client = redis_client
        self.event_id = event_id
        self.rtmp_url = rtmp_url
        self.fps = fps
        self.width = width
        self.height = height
        self.frame_interval = 1.0 / self.fps

    def run(self):
        ffmpeg_cmd = [
            'ffmpeg',
            '-y',
            '-f', 'image2pipe',
            '-vcodec', 'webp',
            '-r', str(self.fps),
            '-s', f'{self.width}x{self.height}',
            '-i', '-',
            '-f', 'lavfi',
            '-i', 'anullsrc=channel_layout=stereo:sample_rate=44100',
            '-c:v', 'libx264',
            '-preset', 'veryfast',
            '-pix_fmt', 'yuv420p',
            '-c:a', 'aac',
            '-b:a', '128k',
            '-shortest',
            '-f', 'flv',
            self.rtmp_url
        ]

        ffmpeg = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE)
        video_key = f"{self.event_id}-video_source-final_frame"

        try:
            while True:
                start_time = time.time()

                # Leer frame desde Redis (como bytes WEBP)
                frame_data = self.redis_client.get(video_key)
                if frame_data is None:
                    print("No hay frame en Redis")
                    time.sleep(self.frame_interval)
                    continue

                ffmpeg.stdin.write(frame_data)

                elapsed = time.time() - start_time
                sleep_time = self.frame_interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    pass
        except KeyboardInterrupt:
            print("Terminando stream...")

        finally:
            ffmpeg.stdin.close()
            ffmpeg.wait()


# Función principal para iniciar el proceso
def main():
    # Configuración de Redis
    redis_client = redis.Redis(host='redis-sigasiga', port=6379, db=0)
    event_id = "47f3okNyYJzs8an9JyjmUc"  # Clave de Redis donde se almacenan los frames
    rtmp_url = "rtmp://a.rtmp.youtube.com/live2/9kvw-ujak-cp6w-4qwg-cx62"
    
    # Crear e iniciar el proceso de emisión RTMP
    emitter = RtmpEmitter(redis_client, event_id, rtmp_url, fps=25, width=1280, height=720)
    emitter.start()

    # Esperar a que el proceso termine (en este caso, nunca termina a menos que se interrumpa)
    emitter.join()

if __name__ == "__main__":
    main()