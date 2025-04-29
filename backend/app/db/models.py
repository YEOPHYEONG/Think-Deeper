# backend/app/db/models.py (기존 파일에 추가)

from sqlalchemy import Column, Integer, String, Text, ForeignKey, TIMESTAMP, func
from sqlalchemy.ext.declarative import declarative_base

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
    state_json = Column(Text, nullable=False)
