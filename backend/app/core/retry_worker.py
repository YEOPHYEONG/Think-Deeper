# backend/app/core/retry_worker.py

from app.core.flush_manager import has_flush_failed, flush_session_to_postgres, clear_flush_failed
from app.core.redis_checkpointer import RedisCheckpointer
from app.core.config import settings

redis_cp = RedisCheckpointer(settings.REDIS_URL, ttl=settings.SESSION_TTL_SECONDS)

async def retry_failed_flush(session_id: str):
    if not await has_flush_failed(session_id):
        return False

    config = {"configurable": {"thread_id": session_id}}
    state = await redis_cp.aget(config)
    if not state:
        print(f"[retry flush] session_id={session_id} - Redis 상태 없음")
        return False

    try:
        await flush_session_to_postgres(session_id, state.get("memory", {}), state.get("messages", []))
        await clear_flush_failed(session_id)
        print(f"[retry flush 성공] session_id={session_id}")
        return True
    except Exception as e:
        print(f"[retry flush 실패] session_id={session_id}: {e}")
        return False
