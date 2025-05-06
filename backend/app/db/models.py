# backend/app/db/models.py (기존 파일에 추가)

from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSON, UUID, JSONB
from datetime import datetime
import uuid

Base = declarative_base()

# 기존 GraphStateRecord는 이미 존재

class MessageRecord(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    thread_id = Column(String, nullable=False, index=True)
    sender = Column(String(10), nullable=False)  # 'user' or 'bot'
    content = Column(Text, nullable=False)
    timestamp = Column(TIMESTAMP, nullable=False, server_default=func.now())

class GraphStateRecord(Base):
    __tablename__ = "graph_state_records"

    thread_id = Column(String, primary_key=True)
    state_json = Column(JSON, nullable=False)  # ✅ 수정된 부분

class SessionStateRecord(Base):
    __tablename__ = "session_state"
    session_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    state = Column(JSONB, nullable=False)
    updated_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, server_default="NOW()")

class SessionTranscriptRecord(Base):
    __tablename__ = "session_transcript"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("session_state.session_id"), nullable=False)
    occurred_at = Column(TIMESTAMP, nullable=False, default=datetime.utcnow, server_default="NOW()")
    role = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
