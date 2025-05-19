import time
import redis
import io
from PIL import Image, ImageDraw, ImageFont
from multiprocessing import Process
import os
import setproctitle

class ScoreboardFrameProcessor(Process):
    def __init__(self, event_id, redis_client, name=None):
        super().__init__(name=name)
        self.event_id = event_id
        self.redis_client = redis_client
        self.fps = 25
        self.frame_time = 1.0 / self.fps
        self.current_dir = str(os.path.dirname(os.path.abspath(__file__)))

    def read_redis_data(self):
        """Read all necessary data from Redis."""
        keys = {
            'local_team': f"{self.event_id}-scoreboard-local_team",
            'visitor_team': f"{self.event_id}-scoreboard-visitor_team",
            'local_points': f"{self.event_id}-scoreboard-local_points",
            'visitor_points': f"{self.event_id}-scoreboard-visitor_points",
            'timer': f"{self.event_id}-scoreboard-timer",
            '24_timer': f"{self.event_id}-scoreboard-24_timer",
            'period': f"{self.event_id}-scoreboard-period",
        }

        data = {}
        for key, redis_key in keys.items():
            data[key] = self.redis_client.get(redis_key)
            if data[key] is not None:
                data[key] = data[key].decode('utf-8')
            else:
                data[key] = ""

        return data
    
    def miliseconds_to_time(self, milliseconds):
        """Convert milliseconds to a formatted time string."""
        seconds = milliseconds // 1000
        minutes = seconds // 60
        seconds = seconds % 60
        milliseconds = str(milliseconds % 1000)[0]
        if minutes < 1:
            return f"{seconds:02}.{milliseconds}"
        return f"{minutes:02}:{seconds:02}"

    def miliseconds_to_24_time(self, milliseconds):
        """Convert milliseconds to a formatted 24-second timer string."""
        seconds = milliseconds // 1000
        milliseconds = str(milliseconds % 1000)[0]
        if seconds < 10:
            return f"{seconds:02}.{milliseconds}"
        return f"{seconds:02}"
    
    def process_frame(self, template, data):
        """Process the template image with the current data."""
        # Create a copy of the template
        frame = template.copy()
        draw = ImageDraw.Draw(frame)

        # Load a font (you'll need to specify the path to a font file)
        try:
            text_font = ImageFont.truetype(f"{self.current_dir}/templates/italic_names.ttf", 80)
            text_font_points = ImageFont.truetype(f"{self.current_dir}/templates/italic_names.ttf", 120)

        except:
            text_font = ImageFont.load_default(50)
            text_font_points = ImageFont.load_default(50)
        try:
            timer_font = ImageFont.truetype(f"{self.current_dir}/templates/numbers.ttf", 80)
            period_font = ImageFont.truetype(f"{self.current_dir}/templates/numbers.ttf", 60)
            timer_font_24 = period_font
        except:
            number_font = ImageFont.load_default(50)
        # Draw the data on the frame
        # Note: You'll need to adjust these coordinates based on your template
        draw.text((646, 225), text = data['local_team'], fill="white", font=text_font, anchor="lb")
        draw.text((635, 350), text = data['visitor_team'], fill="white", font=text_font, anchor="lb")
        draw.text((970, 228), text = data['local_points'], fill="white", font=text_font_points, anchor="lb")
        draw.text((960, 353), text = data['visitor_points'], fill="white", font=text_font_points, anchor="lb")
        draw.text((450, 245), text = self.miliseconds_to_time(int(data['timer'])), fill="white", font=timer_font, anchor="mm")
        draw.text((450, 320), text = self.miliseconds_to_24_time(int(data['24_timer'])), fill="white", font=timer_font_24, anchor="mm")
        draw.text((450, 161), text = f"{data['period']}º", fill="orange", font=period_font, anchor="mm")

        # background = Image.open("templates/background.webp")

        # resize original frame to half frame size
        frame = frame.resize((int(frame.width / 2), int(frame.height / 2)))

        # put frame over background
        # background.paste(frame, (0, 0), frame)
        return frame

    def run(self):
        """Main process loop."""
        setproctitle.setproctitle(f"{self.event_id}-scoreboard_frames")
        # Load the template image
        sleep_time = 1 / 25
        try:
            template = Image.open(f"{self.current_dir}/templates/scoreboard_template.png")
        except FileNotFoundError:
            print("Error: Template image not found!")
            return

        while True:

            # Read data from Redis
            data = self.read_redis_data()

            # Process the frame
            frame = self.process_frame(template, data)

            # Save frame as PNG to bytes
            png_bytes = io.BytesIO()
            frame.save(png_bytes, format='PNG')
            png_bytes = png_bytes.getvalue()

            # Store PNG bytes in Redis
            self.redis_client.set(f"{self.event_id}-scoreboard_frame", png_bytes)

            time.sleep(sleep_time)