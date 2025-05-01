# backend/app/core/redis_checkpointer.py

from redis.asyncio import Redis
import json
from typing import Optional, Dict, Any, List
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage
from langchain_core.load import dumps
import pickle

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
        self.client = Redis.from_url(redis_url, decode_responses=False)
        self.ttl = ttl

    def _key(self, config: Dict[str, Any]) -> str:
        ns = config.get("configurable", {}).get("checkpoint_ns", "") or "default"
        thread_id = config.get("configurable", {}).get("thread_id", "")
        checkpoint_id = config.get("configurable", {}).get("checkpoint_id", "") or "latest"
        return f"checkpointer:{ns}:{thread_id}:{checkpoint_id}"

    async def aget(self, config: Dict[str, Any]) -> Optional[dict]:
        raw = await self.client.get(self._key(config))
        if raw is None:
            return None
        state = pickle.loads(raw)

        # ❗ 메시지 복원 처리
        if "messages" in state and isinstance(state["messages"], list):
            state["messages"] = deserialize_messages(state["messages"])

        return state

    async def aset(self, config: Dict[str, Any], checkpoint: dict):
        key = self._key(config)
        print(f"[RedisCheckpointer] aset 호출됨")
        print(f"  - thread_id: {config['configurable']['thread_id']}")
        print(f"  - keys: {list(checkpoint.keys())}")  # <-- 여기가 에러났던 부분

        # 실제 저장
        data = pickle.dumps(checkpoint)
        await self.client.set(key, data, ex=self.ttl)


    async def adelete(self, config: Dict[str, Any]) -> None:
        await self._redis.delete(self._key(config))

    def get(self, config: Dict[str, Any]) -> Optional[dict]:
        raise NotImplementedError("동기 get은 테스트 용도로만 구현 필요")

    def set(self, config: Dict[str, Any], state: dict) -> None:
        raise NotImplementedError("동기 set은 테스트 용도로만 구현 필요")

    def delete(self, config: Dict[str, Any]) -> None:
        raise NotImplementedError("동기 delete은 테스트 용도로만 구현 필요")
