# backend/tests/core/test_orchestration.py

import pytest
from app.core.orchestration import run_conversation_turn_langgraph

@pytest.mark.asyncio
async def test_run_conversation_turn_langgraph():
    session_id = "test-session-graph"
    user_input = "이 앱은 어떤 기능이 있나요?"

    # 실제 Redis/DB 접근 -> test 환경에서 돌릴 것
    response = await run_conversation_turn_langgraph(session_id=session_id, user_input=user_input)

    assert isinstance(response, str)
    assert len(response) > 0
    print("Graph 흐름 응답:", response)
