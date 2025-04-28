# backend/app/core/redis_checkpointer.py

import pickle
from redis import Redis
from app.core.config import get_settings

settings = get_settings()

class RedisCheckpointer:
    def __init__(self, redis_url: str, ttl: int = 3600):
        self._redis = Redis.from_url(redis_url) if redis_url else None
        self._ttl = ttl

    def _key(self, config: dict) -> str:
        return f"langgraph:state:{config['configurable']['thread_id']}"

    def get(self, config: dict):
        if not self._redis:
            return None
        raw = self._redis.get(self._key(config))
        return pickle.loads(raw) if raw else None

    def set(self, config: dict, state):
        if not self._redis:
            return
        raw = pickle.dumps(state)
        self._redis.set(self._key(config), raw, ex=self._ttl)

    def delete(self, config: dict):
        if not self._redis:
            return
        self._redis.delete(self._key(config))
