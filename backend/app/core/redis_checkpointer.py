# backend/app/core/redis_checkpointer.py

from redis.asyncio import Redis
import json
from typing import Optional, Dict, Any

SESSION_PREFIX = "session:"

class RedisCheckpointer:
    def __init__(self, redis_url: str, ttl: int = 3600):
        self._redis = Redis.from_url(redis_url)
        self.ttl = ttl

    def _key(self, config: Dict[str, Any]) -> str:
        return SESSION_PREFIX + config["configurable"]["thread_id"]

    async def aget(self, config: Dict[str, Any]) -> Optional[dict]:
        raw = await self._redis.get(self._key(config))
        if raw is None:
            return None
        return json.loads(raw)

    async def aset(self, config: Dict[str, Any], state: dict) -> None:
        await self._redis.set(self._key(config), json.dumps(state), ex=self.ttl)

    async def adelete(self, config: Dict[str, Any]) -> None:
        await self._redis.delete(self._key(config))

    def get(self, config: Dict[str, Any]) -> Optional[dict]:
        raise NotImplementedError("동기 get은 테스트 용도로만 구현 필요")

    def set(self, config: Dict[str, Any], state: dict) -> None:
        raise NotImplementedError("동기 set은 테스트 용도로만 구현 필요")

    def delete(self, config: Dict[str, Any]) -> None:
        raise NotImplementedError("동기 delete은 테스트 용도로만 구현 필요")
