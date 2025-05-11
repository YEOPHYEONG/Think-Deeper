# backend/tests/core/test_why_orchestration.py

import pytest
from app.core.why_orchestration import run_why_exploration_turn

@pytest.mark.asyncio
async def test_run_why_exploration_turn():
    session_id = "test-session-why"
    initial_idea = "이 앱으로 목표를 관리하고 싶습니다."

    # 실제 Redis/DB에 의존하므로 사전에 세션이 존재하지 않아도 되는지 확인 필요
    response = await run_why_exploration_turn(session_id=session_id, user_input=initial_idea)

    assert isinstance(response, str)
    assert len(response) > 0
    print("Why 흐름 응답:", response)
