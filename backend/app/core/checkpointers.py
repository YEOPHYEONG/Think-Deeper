# backend/app/core/checkpointers.py

import pickle
import asyncio
from typing import NamedTuple, Optional, Dict, Any, Iterator, AsyncIterator

from .sql_checkpointer import SQLCheckpointer
from .redis_checkpointer import RedisCheckpointer

class CheckpointTuple(NamedTuple):
    checkpoint: dict
    metadata: dict
    parent_config: Optional[dict]
    pending_writes: Optional[Any]
    id: Optional[str]
    versions_seen: Optional[dict]
    step: Optional[int]
    pending_sends: Optional[Any]
    version: Optional[str]
    config: Optional[Dict[str, Any]]

class CombinedCheckpointer:
    def __init__(
        self,
        db_session_factory,
        redis_url: str,
        ttl: int = 3600,
    ):
        self.sql_cp = SQLCheckpointer(db_session_factory)
        self.redis_cp = RedisCheckpointer(redis_url, ttl)

    # ----------------------
    # 비동기 get (raw state dict 반환)
    # ----------------------
    async def aget(self, config: Dict[str, Any]) -> Optional[dict]:
        """
        LangGraph가 호출하는 async get: raw state dict 반환
        """
        state = self.redis_cp.get(config)
        if state is None:
            state = await self.sql_cp.aget(config)
        return state

    # ----------------------
    # 비동기 get_tuple (CheckpointTuple 반환)
    # ----------------------
    async def aget_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        raw = await self.aget(config)
        if raw is None:
            return None
        metadata = raw.get("metadata", {})
        versions_seen = raw.get("versions_seen")
        if not isinstance(versions_seen, dict):
            versions_seen = {}  # 강제 보정

        return CheckpointTuple(
            checkpoint=raw,
            metadata=metadata,
            parent_config=None,
            pending_writes=None,
            id=None,
            versions_seen=versions_seen,
            step=None,
            pending_sends=None,
            version=None,
            config=config,
        )
    
    # ----------------------
    # 비동기 put
    # ----------------------
    async def aput(self, config: Dict[str, Any], checkpoint: dict, metadata: dict, versions_seen: dict) -> None:
        checkpoint["metadata"] = metadata
        checkpoint["versions_seen"] = versions_seen
        self.redis_cp.set(config, checkpoint)
        await self.sql_cp.aset(config, checkpoint)

    # ----------------------
    # 비동기 put_writes (no-op 또는 별도 저장)
    # ----------------------
    async def aput_writes(self, config: Dict[str, Any], writes: Any, task_id: str, task_path: str = "") -> None:
        return None

    # ----------------------
    # 비동기 delete (단일 쓰레드)
    # ----------------------
    async def adelete(self, config: Dict[str, Any]) -> None:
        self.redis_cp.delete(config)
        await self.sql_cp.adelete(config)

    async def adelete_thread(self, config: Dict[str, Any]) -> None:
        """Alias for adelete"""
        return await self.adelete(config)

    # ----------------------
    # 비동기 list
    # ----------------------
    async def alist(self, config: Dict[str, Any]) -> AsyncIterator[CheckpointTuple]:
        for tup in self.list(config):
            yield tup

    # ----------------------
    # 동기 get (raw state dict 반환)
    # ----------------------
    def get(self, config: Dict[str, Any]) -> Optional[dict]:
        return asyncio.get_event_loop().run_until_complete(self.aget(config))

    # ----------------------
    # 동기 get_tuple
    # ----------------------
    def get_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        return asyncio.get_event_loop().run_until_complete(self.aget_tuple(config))

    # ----------------------
    # 동기 put
    # ----------------------
    def put(self, config: Dict[str, Any], checkpoint: dict) -> None:
        asyncio.get_event_loop().run_until_complete(
            self.aput(config, checkpoint, checkpoint.get("metadata", {}), checkpoint.get("versions_seen", {}))
        )

    # ----------------------
    # 동기 put_writes
    # ----------------------
    def put_writes(self, config: Dict[str, Any], writes: Any, task_id: str, task_path: str = "") -> None:
        asyncio.get_event_loop().run_until_complete(
            self.aput_writes(config, writes, task_id, task_path)
        )

    # ----------------------
    # 동기 delete_thread
    # ----------------------
    def delete_thread(self, thread_id: str) -> None:
        config = {"configurable": {"thread_id": thread_id}}
        self.redis_cp.delete(config)
        asyncio.get_event_loop().run_until_complete(self.sql_cp.adelete(config))

    # ----------------------
    # 동기 list
    # ----------------------
    def list(self, config: Dict[str, Any]) -> Iterator[CheckpointTuple]:
        if tup := self.get_tuple(config):
            yield tup

    # ----------------------
    # 다음 버전 생성 로직
    # ----------------------
    def get_next_version(self, max_version: Optional[int], channel_state: Any) -> int:
        return (max_version or 0) + 1
