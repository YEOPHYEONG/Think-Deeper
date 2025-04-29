# backend/app/core/state_manager.py

import uuid
from typing import Optional
from app.core.session_store import save_session_initial_info
from app.core.session_store import get_session_initial_info as get_session_info_from_redis
import asyncio
import os  # ✅ 추가됨

async def create_new_session(topic: str, initial_agent_type: Optional[str] = None) -> str:
    """ 새로운 세션 ID 생성 + Redis에 초기 정보 저장 """
    new_session_id = str(uuid.uuid4())
    agent_type = initial_agent_type or "critic"

    if os.getenv("TESTING") == "1":
        await save_session_initial_info(new_session_id, topic, agent_type)
    else:
        asyncio.create_task(
            save_session_initial_info(new_session_id, topic, agent_type)
        )

    print(f"세션 초기 정보 저장됨 (Redis): ID={new_session_id}, 주제='{topic}', 초기 에이전트='{agent_type}'")
    return new_session_id

async def get_session_initial_info(session_id: str):
    return await get_session_info_from_redis(session_id)

async def delete_session_initial_info(session_id: str) -> bool:
    from app.core.session_store import r, SESSION_PREFIX
    result = await r.delete(SESSION_PREFIX + session_id)
    if result:
        print(f"세션 초기 정보 삭제됨 (Redis): ID={session_id}")
        return True
    return False
