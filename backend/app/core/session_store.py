# backend/app/core/session_store.py

import json
import redis.asyncio as redis
from app.core.config import settings

r = redis.from_url(settings.REDIS_URL)

SESSION_PREFIX = "session_info:"

async def save_session_initial_info(session_id: str, topic: str, agent_type: str):
    key = SESSION_PREFIX + session_id
    value = json.dumps({"topic": topic, "agent_type": agent_type})
    await r.set(key, value, ex=settings.SESSION_TTL_SECONDS)

async def get_session_initial_info(session_id: str) -> dict:
    key = SESSION_PREFIX + session_id
    raw = await r.get(key)
    if raw is None:
        return {}
    return json.loads(raw)
