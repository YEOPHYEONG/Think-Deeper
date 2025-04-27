# backend/app/core/redis_checkpointer.py
import pickle
from langgraph.checkpoint.base import Checkpointer
from redis import Redis
from ..core.config import get_settings

settings = get_settings()

class RedisCheckpointer(Checkpointer):
    def __init__(self):
        self._redis = Redis.from_url(settings.REDIS_URL)

    def _key(self, config): return f"langgraph:state:{config['configurable']['thread_id']}"

    def get(self, config):
        raw = self._redis.get(self._key(config))
        return pickle.loads(raw) if raw else None

    def set(self, config, state):
        raw = pickle.dumps(state)
        # TTL도 설정 가능 (예: EX=3600)
        self._redis.set(self._key(config), raw, ex=settings.SESSION_TTL_SECONDS)

    def delete(self, config):
        self._redis.delete(self._key(config))
