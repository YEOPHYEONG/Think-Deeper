# backend/app/core/recovery_manager.py

from app.db.session import get_db_session_async
from app.db.models import GraphStateRecord, MessageRecord
from app.core.redis_checkpointer import RedisCheckpointer
from app.core.config import settings
from sqlalchemy.future import select

import pickle

redis_cp = RedisCheckpointer(settings.REDIS_URL, ttl=settings.SESSION_TTL_SECONDS)

async def restore_session_to_redis(session_id: str) -> bool:
    """PostgreSQL에 저장된 세션 memory + messages를 Redis에 복구"""
    async with get_db_session_async() as db:
        # 1. memory 복구
        result = await db.execute(
            select(GraphStateRecord).where(GraphStateRecord.thread_id == session_id)
        )
        record = result.scalar_one_or_none()
        if not record:
            print(f"[복구 실패] session_id={session_id} 에 대한 메모리 상태 없음.")
            return False

        memory_state = record.state_json

        # 2. messages 복구
        result = await db.execute(
            select(MessageRecord).where(MessageRecord.thread_id == session_id).order_by(MessageRecord.timestamp)
        )
        message_records = result.scalars().all()
        messages = []
        for msg in message_records:
            messages.append({
                "sender": msg.sender,
                "content": msg.content
            })

        # 3. Redis에 저장
        redis_state = {
            "memory": memory_state.get("memory", {}),
            "messages": messages,
        }
        config = {"configurable": {"thread_id": session_id}}
        redis_cp.set(config, redis_state)
        print(f"[복구 성공] session_id={session_id} Redis에 복원 완료.")

        return True
