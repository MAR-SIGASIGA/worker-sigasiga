import time
import redis
import os
from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
import io

load_dotenv()

def start_process(redis_client, event_id):
    print(f"Starting final video process for event {event_id}")
    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"Directorio actual: {current_dir}")
    default_image_path = f"{current_dir}/resources/default.jpg"

    default_img = Image.open(default_image_path)
    img_byte_arr = io.BytesIO()
    default_img.save(img_byte_arr, format='JPEG')
    img_byte_arr = img_byte_arr.getvalue()

    selected_source = "default"
    selected_source_key = f"{event_id}-video_source-{selected_source}"
    redis_client.set(selected_source_key, img_byte_arr)
    redis_client.set(f"{event_id}-selected_source", selected_source.encode('utf-8'))

    while True:
        selected_source_name = redis_client.get(f"{event_id}-selected_source").decode('utf-8')
        print(f"Selected source: {selected_source_name}")
        selected_source_frame = redis_client.get(f"{event_id}-video_source-{selected_source_name}")
        # selected_source_frame = redis_client.brpop("processed_frames", timeout=0)[1]
        redis_key = f"{event_id}-final_video_frame"
        try:
            redis_client.set(redis_key, selected_source_frame)
        except Exception as e:
            print(f"Error al guardar el frame en Redis: {e}")
            redis_client.set(redis_key, img_byte_arr)
        time.sleep(1/25)
        # if selected_source_frame:

        #     with Image.open(io.BytesIO(selected_source_frame)) as img:

        #         current_time = datetime.now().strftime("%H:%M:%S")


        #         draw = ImageDraw.Draw(img)


        #         font = ImageFont.load_default()

        #         bbox = draw.textbbox((0, 0), current_time, font=font)
        #         text_width = bbox[2] - bbox[0]  # Ancho del texto
        #         text_height = bbox[3] - bbox[1]  # Alto del texto

        #         position = (img.width - text_width - 10, img.height - text_height - 10)

        #         draw.text(position, current_time, font=font, fill="white")


        #         img_byte_arr = io.BytesIO()
        #         img.save(img_byte_arr, format='PNG')
        #         img_byte_arr = img_byte_arr.getvalue()

        #         redis_key = f"{event_id}-final_video_frame"
        #         redis_client.set(redis_key, img_byte_arr)
        #         print(f"Frame procesado y guardado en Redis con la clave: {redis_key}")

