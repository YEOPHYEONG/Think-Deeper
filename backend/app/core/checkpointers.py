# backend/app/core/checkpointers.py

import pickle
from sqlalchemy.orm import Session
from redis import Redis
from typing import NamedTuple

from ..db.models import GraphStateRecord
import uuid
from typing import Optional


class SQLCheckpointer:
    def __init__(self, db_session: Session):
        self.db = db_session

    def get(self, config):
        tid = config["configurable"]["thread_id"]
        return self.db.get(GraphStateRecord, tid)

    def set(self, config, state):
        tid = config["configurable"]["thread_id"]
        rec = self.db.get(GraphStateRecord, tid)
        if rec:
            rec.state_json = state
        else:
            rec = GraphStateRecord(thread_id=tid, state_json=state)
            self.db.add(rec)
        self.db.commit()

    def delete(self, config):
        tid = config["configurable"]["thread_id"]
        self.db.query(GraphStateRecord).filter_by(thread_id=tid).delete()
        self.db.commit()

class RedisCheckpointer:
    def __init__(self, redis_url: str, ttl: int = 3600):
        if redis_url:
            self._redis = Redis.from_url(redis_url)
        else:
            self._redis = None
        self._ttl = ttl

    def _key(self, config):
        return f"langgraph:state:{config['configurable']['thread_id']}"

    def get(self, config):
        if not self._redis:
            return None
        raw = self._redis.get(self._key(config))
        return pickle.loads(raw) if raw else None

    def set(self, config, state):
        if not self._redis:
            return
        raw = pickle.dumps(state)
        self._redis.set(self._key(config), raw, ex=self._ttl)

    def delete(self, config):
        if not self._redis:
            return
        self._redis.delete(self._key(config))

class CheckpointTuple(NamedTuple):
    checkpoint: dict
    metadata: dict
    parent_config: Optional[dict] = None
    pending_writes: Optional[list] = None
    id: Optional[str] = None
    versions_seen: Optional[dict] = None
    step: Optional[int] = 0
    pending_sends: Optional[list] = []
    version: Optional[str] = None
    config: Optional[dict] = None   # ✅ 이 줄을 추가해줘야 한다!
    
class CombinedCheckpointer:
    def __init__(self, db_session: Session, redis_url: str = None, ttl: int = 3600):
        self.sql_cp = SQLCheckpointer(db_session)
        self.redis_cp = RedisCheckpointer(redis_url, ttl)

    def _extract_state(self, record_or_dict):
        if record_or_dict is None:
            return None
        if isinstance(record_or_dict, dict):
            return record_or_dict
        return record_or_dict.state_json

    async def aget(self, config):
        redis_state = self.redis_cp.get(config)
        if redis_state:
            return redis_state
        sql_record = self.sql_cp.get(config)
        state = self._extract_state(sql_record)
        if state:
            self.redis_cp.set(config, state)
        return state

    async def aput(self, config, checkpoint, metadata, versions_seen):
        """langgraph가 요구하는 비동기 put 메서드 (전체 상태 + 메타데이터 저장용)"""
        # checkpoint dict 안에 메타데이터와 versions_seen을 저장해준다.
        checkpoint["metadata"] = metadata
        checkpoint["versions_seen"] = versions_seen
        self.set(config, checkpoint)

    async def aput_writes(self, task_id, writes, config):
        """langgraph가 요구하는 비동기 writes 적용"""
        current = await self.aget(config)
        if not current:
            current = {
                "id": str(uuid.uuid4()),
                "channel_values": {},
                "channel_versions": {},
                "next": {},
                "versions_seen": {},
                "pending_sends": [],
                "step": 0,
            }
        for key, value in writes:
            if key == "step":
                current["step"] = value
            elif key == "pending_sends":
                current["pending_sends"] = value
            elif key == "next":
                current["next"] = value
            elif key == "channel_values":
                current["channel_values"] = value
            elif key == "channel_versions":
                current["channel_versions"] = value
            elif key == "versions_seen":
                current["versions_seen"] = value
            elif key == "messages":
                current.setdefault("messages", []).extend(value)
            else:
                current[key] = value

        self.set(config, current)

    def get(self, config):
        redis_state = self.redis_cp.get(config)
        if redis_state:
            return redis_state
        sql_record = self.sql_cp.get(config)
        state = self._extract_state(sql_record)
        if state:
            self.redis_cp.set(config, state)
        return state

    def set(self, config, state):
        self.sql_cp.set(config, state)
        self.redis_cp.set(config, state)

    def delete(self, config):
        self.sql_cp.delete(config)
        self.redis_cp.delete(config)

    def get_next_version(self, max_version, channel_state):
        return (max_version or 0) + 1

    async def aget_tuple(self, config):
        state = await self.aget(config)
        if state is None:
            state = {
                "id": str(uuid.uuid4()),
                "channel_values": {},
                "channel_versions": {},
                "next": {},
                "versions_seen": {},
                "pending_sends": [],
                "step": 0,
            }
        elif "id" not in state:
            state["id"] = str(uuid.uuid4())

        return CheckpointTuple(
            checkpoint=state,
            version=None,
            config=config,
            parent_config=config,
            metadata={"step": state["step"]},
            pending_writes=[],
            step=state["step"],
            pending_sends=state["pending_sends"],
            id=state["id"],
            versions_seen=state["versions_seen"]
        )

    def get_tuple(self, config):
        state = self.get(config)
        if state is None:
            state = {
                "id": str(uuid.uuid4()),
                "channel_values": {},
                "channel_versions": {},
                "next": {},
                "versions_seen": {},
                "pending_sends": [],
                "step": 0,
            }
        elif "id" not in state:
            state["id"] = str(uuid.uuid4())

        return CheckpointTuple(
            checkpoint=state,
            version=None,
            config=config,
            parent_config=config,
            metadata={"step": state["step"]},
            pending_writes=[],
            step=state["step"],
            pending_sends=state["pending_sends"],
            id=state["id"],
            versions_seen=state["versions_seen"]
        )
