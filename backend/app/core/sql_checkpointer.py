# backend/app/core/sql_checkpointer.py
import json
from sqlalchemy.orm import Session
from langgraph.checkpoint.base import Checkpointer
from ..db.models import GraphStateRecord  # thread_id, state_json

class SQLCheckpointer(Checkpointer):
    def __init__(self, db_session: Session):
        self.db = db_session

    def get(self, config: dict):
        tid = config["configurable"]["thread_id"]
        rec = self.db.query(GraphStateRecord).get(tid)
        return rec.state_json if rec else None

    def set(self, config: dict, state) -> None:
        tid = config["configurable"]["thread_id"]
        payload = state.values  # GraphState 또는 WhyGraphState.values
        rec = self.db.query(GraphStateRecord).get(tid)
        if rec:
            rec.state_json = payload
        else:
            rec = GraphStateRecord(thread_id=tid, state_json=payload)
            self.db.add(rec)
        self.db.commit()

    def delete(self, config: dict) -> None:
        tid = config["configurable"]["thread_id"]
        self.db.query(GraphStateRecord).filter_by(thread_id=tid).delete()
        self.db.commit()
