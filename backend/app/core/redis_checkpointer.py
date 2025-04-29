# backend/app/core/redis_checkpointer.py

from redis.asyncio import Redis
import json
from typing import Optional, Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.load import dumps

SESSION_PREFIX = "session:"

def deserialize_messages(messages: List[Dict[str, Any]]) -> List[BaseMessage]:
    """dict를 다시 메시지 객체로 복원."""
    deserialized = []
    for msg in messages:
        if isinstance(msg, dict) and "type" in msg and "content" in msg:
            if msg["type"] == "human":
                deserialized.append(HumanMessage(content=msg["content"]))
            elif msg["type"] == "ai":
                deserialized.append(AIMessage(content=msg["content"]))
            else:
                deserialized.append(msg)  # 알 수 없는 타입이면 dict 그대로
        else:
            deserialized.append(msg)
    return deserialized

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
        state = json.loads(raw)

        # ❗ 메시지 복원 처리
        if "messages" in state and isinstance(state["messages"], list):
            state["messages"] = deserialize_messages(state["messages"])

        return state

    async def aset(self, config: Dict[str, Any], state: dict) -> None:
        await self._redis.set(self._key(config), dumps(state), ex=self.ttl)


    async def adelete(self, config: Dict[str, Any]) -> None:
        await self._redis.delete(self._key(config))

    def get(self, config: Dict[str, Any]) -> Optional[dict]:
        raise NotImplementedError("동기 get은 테스트 용도로만 구현 필요")

    def set(self, config: Dict[str, Any], state: dict) -> None:
        raise NotImplementedError("동기 set은 테스트 용도로만 구현 필요")

    def delete(self, config: Dict[str, Any]) -> None:
        raise NotImplementedError("동기 delete은 테스트 용도로만 구현 필요")
