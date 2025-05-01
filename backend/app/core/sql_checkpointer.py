# backend/app/core/sql_checkpointer.py

import json
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.models import GraphStateRecord
from langchain_core.load import dumps  # 상단 import

class SQLCheckpointer:
    def __init__(self, db_session_factory):
        # db_session_factory는 async_sessionmaker 또는 asynccontextmanager
        self.db_session_factory = db_session_factory

    async def aget(self, config: dict):
        session_id = config["configurable"]["thread_id"]
        async with self.db_session_factory() as session:  # AsyncSession 팩토리 호출
            result = await session.execute(
                select(GraphStateRecord).where(GraphStateRecord.thread_id == session_id)
            )
            record = result.scalar_one_or_none()
            return record.state_json if record else None

    async def aset(self, config: dict, state: dict) -> None:
        print("[SQLCheckpointer] aset 호출됨")
        print("  - thread_id:", config.get("configurable", {}).get("thread_id"))
        session_id = config["configurable"]["thread_id"]

        # 💡 LangChain 메시지 객체 등 JSON 직렬화가 안되는 항목을 문자열로 변환
        json_serialized_state = json.loads(dumps(state))

        async with self.db_session_factory() as session:
            result = await session.execute(
                select(GraphStateRecord).where(GraphStateRecord.thread_id == session_id)
            )
            record = result.scalar_one_or_none()
            if record:
                record.state_json = json_serialized_state
            else:
                session.add(GraphStateRecord(thread_id=session_id, state_json=json_serialized_state))
            await session.commit()

    async def adelete(self, config: dict) -> None:
        session_id = config["configurable"]["thread_id"]
        async with self.db_session_factory() as session:
            result = await session.execute(
                select(GraphStateRecord).where(GraphStateRecord.thread_id == session_id)
            )
            record = result.scalar_one_or_none()
            if record:
                await session.delete(record)
                await session.commit()
