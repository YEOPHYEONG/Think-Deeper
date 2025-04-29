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
    def __init__(self, redis_cp: RedisCheckpointer, sql_cp: SQLCheckpointer):
        self.redis_cp = redis_cp
        self.sql_cp = sql_cp

    async def aget(self, config: Dict[str, Any]) -> Optional[dict]:
        state = await self.redis_cp.aget(config)
        if state is None:
            state = await self.sql_cp.aget(config)
        return state

    async def aget_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        raw = await self.aget(config)
        if raw is None:
            return None
        metadata = raw.get("metadata", {})
        versions_seen = raw.get("versions_seen")
        if not isinstance(versions_seen, dict):
            versions_seen = {}

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

    async def aput(self, config: Dict[str, Any], checkpoint: dict, metadata: dict, versions_seen: dict) -> None:
        checkpoint["metadata"] = metadata
        checkpoint["versions_seen"] = versions_seen
        await self.redis_cp.aset(config, checkpoint)
        await self.sql_cp.aset(config, checkpoint)

    async def aput_writes(self, config: Dict[str, Any], writes: Any, task_id: str, task_path: str = "") -> None:
        return None

    async def adelete(self, config: Dict[str, Any]) -> None:
        await self.redis_cp.adelete(config)
        await self.sql_cp.adelete(config)

    async def adelete_thread(self, config: Dict[str, Any]) -> None:
        return await self.adelete(config)

    async def alist(self, config: Dict[str, Any]) -> AsyncIterator[CheckpointTuple]:
        for tup in self.list(config):
            yield tup

    def get(self, config: Dict[str, Any]) -> Optional[dict]:
        return asyncio.get_event_loop().run_until_complete(self.aget(config))

    def get_tuple(self, config: Dict[str, Any]) -> Optional[CheckpointTuple]:
        return asyncio.get_event_loop().run_until_complete(self.aget_tuple(config))

    def put(self, config: Dict[str, Any], checkpoint: dict) -> None:
        asyncio.get_event_loop().run_until_complete(
            self.aput(config, checkpoint, checkpoint.get("metadata", {}), checkpoint.get("versions_seen", {}))
        )

    def put_writes(self, config: Dict[str, Any], writes: Any, task_id: str, task_path: str = "") -> None:
        asyncio.get_event_loop().run_until_complete(
            self.aput_writes(config, writes, task_id, task_path)
        )

    def delete_thread(self, thread_id: str) -> None:
        config = {"configurable": {"thread_id": thread_id}}
        asyncio.get_event_loop().run_until_complete(self.redis_cp.adelete(config))
        asyncio.get_event_loop().run_until_complete(self.sql_cp.adelete(config))

    def list(self, config: Dict[str, Any]) -> Iterator[CheckpointTuple]:
        if tup := self.get_tuple(config):
            yield tup

    def get_next_version(self, max_version: Optional[int], channel_state: Any) -> int:
        return (max_version or 0) + 1
