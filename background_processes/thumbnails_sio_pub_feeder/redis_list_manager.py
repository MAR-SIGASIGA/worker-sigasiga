class RedisListManager:
    def __init__(self, redis_client=None):
        self.redis_client = redis_client

    def get_all(self, key):
        """Devuelve todos los elementos de la lista en forma de strings."""
        elements = self.redis_client.lrange(key, 0, -1)
        return [el.decode('utf-8') for el in elements]

    def remove_value(self, key, value):
        """
        Elimina todas las apariciones de un valor de la lista.
        Redis LREM con count=0 elimina todas las coincidencias.
        """
        if isinstance(value, str):
            value = value.encode('utf-8')
        return self.redis_client.lrem(key, 0, value)

    def add_to_list(self, key, value, to_end=True):
        """Agrega un valor a la lista; por defecto al final (RPUSH)."""
        if isinstance(value, str):
            value = value.encode('utf-8')
        if to_end:
            return self.redis_client.rpush(key, value)
        else:
            return self.redis_client.lpush(key, value)