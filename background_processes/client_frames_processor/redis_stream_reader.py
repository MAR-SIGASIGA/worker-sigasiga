import io
import threading

class RedisStreamReader(io.RawIOBase):
    def __init__(self, redis_client, redis_key):
        self.redis_client = redis_client
        self.redis_key = redis_key
        self.buffer = bytearray()
        self.lock = threading.Lock()
        self.data_available = threading.Event()
        self.stop_flag = False

        # Arrancar el thread que va trayendo datos de Redis
        self.thread = threading.Thread(target=self._fetch_data, daemon=True)
        self.thread.start()

    def _fetch_data(self):
        while not self.stop_flag:
            # Esperar datos bloqueando (BRPOP es atómico y bloqueante)
            result = self.redis_client.brpop(self.redis_key, timeout=0)
            if result:
                _, data = result
                with self.lock:
                    print(f"📤 Datos recibidos de Redis: {len(data)} bytes")
                    self.buffer.extend(data)
                    self.data_available.set()

    def read(self, size=-1):
        while True:
            with self.lock:
                if self.buffer:
                    if size == -1 or size > len(self.buffer):
                        size = len(self.buffer)
                    data = self.buffer[:size]
                    del self.buffer[:size]
                    return bytes(data)
            # Esperar hasta que haya más datos
            self.data_available.wait()
            self.data_available.clear()
    def readable(self):
        return True

    def seekable(self):
        return False

    def close(self):
        self.stop_flag = True
        self.thread.join()