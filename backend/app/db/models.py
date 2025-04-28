# backend/app/db/models.py

from sqlalchemy import Column, String, JSON
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class GraphStateRecord(Base):
    __tablename__ = "graph_state_records"
    thread_id = Column(String, primary_key=True, index=True)
    state_json = Column(JSON, nullable=False)
