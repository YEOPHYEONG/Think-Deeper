# backend/app/core/flush_manager.py (새 파일 만들자)

from app.db.models import GraphStateRecord, MessageRecord
from app.db.session import get_db_session_async
from app.core.session_store import r  # redis.from_url(...)

async def flush_session_to_postgres(session_id: str, memory_state: dict, messages: list):
    """Redis MemorySaver 데이터를 PostgreSQL에 저장"""
    async with get_db_session_async() as db:
        # GraphState 저장
        result = await db.execute(
            select(GraphStateRecord).where(GraphStateRecord.thread_id == session_id)
        )
        record = result.scalar_one_or_none()

        if record:
            record.state_json = memory_state
        else:
            record = GraphStateRecord(thread_id=session_id, state_json=memory_state)
            db.add(record)

        # Messages 저장
        for msg in messages:
            if isinstance(msg, dict):
                sender = msg.get("sender", "bot")  # 'user' or 'bot'
                content = msg.get("content", "")
            else:
                # 메시지 객체가 아니라 dict라면 패스하거나 raise
                continue

            message_record = MessageRecord(
                thread_id=session_id,
                sender=sender,
                content=content
            )
            db.add(message_record)

        await db.commit()

FAILED_FLUSH_KEY_PREFIX = "flush_failed:"

async def mark_flush_failed(session_id: str):
    key = FAILED_FLUSH_KEY_PREFIX + session_id
    await r.set(key, "1", ex=86400)  # 1일 보존

async def clear_flush_failed(session_id: str):
    key = FAILED_FLUSH_KEY_PREFIX + session_id
    await r.delete(key)

async def has_flush_failed(session_id: str) -> bool:
    key = FAILED_FLUSH_KEY_PREFIX + session_id
    return await r.exists(key) > 0
