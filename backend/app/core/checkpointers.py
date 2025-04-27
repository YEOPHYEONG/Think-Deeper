# backend/app/core/checkpointers.py

import pickle, json
from sqlalchemy.orm import Session
from redis import Redis
from ..db.session import get_db_session
from ..db.models import GraphStateRecord  # SQLAlchemy 모델


class SQLCheckpointer:
    def __init__(self, db_session: Session):
        self.db = db_session

    def get(self, cfg):
        tid = cfg["configurable"]["thread_id"]
        rec = self.db.query(GraphStateRecord).get(tid)
        return rec.state_json if rec else None

    def set(self, cfg, state):
        tid = cfg["configurable"]["thread_id"]
        payload = state.values
        rec = self.db.query(GraphStateRecord).get(tid)
        if rec:
            rec.state_json = payload
        else:
            rec = GraphStateRecord(thread_id=tid, state_json=payload)
            self.db.add(rec)
        self.db.commit()

    def delete(self, cfg):
        tid = cfg["configurable"]["thread_id"]
        self.db.query(GraphStateRecord).filter_by(thread_id=tid).delete()
        self.db.commit()


class RedisCheckpointer:
    def __init__(self, redis_url: str, ttl: int = 3600):
        if redis_url:
            self._redis = Redis.from_url(redis_url)
        else:
            self._redis = None
        self._ttl = ttl

    def _key(self, cfg):
        return f"langgraph:state:{cfg['configurable']['thread_id']}"

    def get(self, cfg):
        if not self._redis:
            return None
        raw = self._redis.get(self._key(cfg))
        return pickle.loads(raw) if raw else None

    def set(self, cfg, state):
        if not self._redis:
            return
        raw = pickle.dumps(state)
        self._redis.set(self._key(cfg), raw, ex=self._ttl)


    def delete(self, cfg):
        if not self._redis:
            return
        self._redis.delete(self._key(cfg))


class CombinedCheckpointer:
    def __init__(self, db_session: Session, redis_url: str, ttl: int = 3600):
        self.sql_cp = SQLCheckpointer(db_session)
        self.redis_cp = RedisCheckpointer(redis_url, ttl)

    def get(self, cfg):
        st = self.redis_cp.get(cfg) or self.sql_cp.get(cfg)
        if st:
            self.redis_cp.set(cfg, st)
        return st

    def set(self, cfg, state):
        self.sql_cp.set(cfg, state)
        self.redis_cp.set(cfg, state)

    def delete(self, cfg):
        self.sql_cp.delete(cfg)
        self.redis_cp.delete(cfg)
