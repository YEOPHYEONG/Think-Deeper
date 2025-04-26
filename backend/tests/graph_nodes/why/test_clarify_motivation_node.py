# backend/tests/graph_nodes/why/test_clarify_motivation_node.py

import pytest
from unittest.mock import AsyncMock, MagicMock

# 테스트 대상 함수 및 관련 클래스 임포트
from backend.app.graph_nodes.why.clarify_motivation_node import clarify_motivation_node, MotivationClarityOutput
# from backend.app.models.why_graph_state import WhyGraphState # 실제 정의된 WhyGraphState 임포트 가정
from backend.app.models.graph_state import GraphState as WhyGraphState # 임시 (실제 정의된 것으로 교체 필요)
from langchain_core.messages import AIMessage, HumanMessage

pytestmark = pytest.mark.asyncio

# --- Test Case 1: Motivation is Clear ---
async def test_clarify_motivation_when_clear(mocker):
    """
    동기가 명확하다고 판단될 때, 상태 업데이트가 올바른지 테스트
    (motivation_clear=True, final_motivation_summary 설정, messages 업데이트 없음)
    """
    # --- Mocking Setup ---
    mock_summary = "사용자는 회의록 작성 시간을 줄여 핵심 업무에 집중하고 싶어합니다."
    mock_llm_response = MotivationClarityOutput(
        is_motivation_clear=True,
        clarification_question=None, # 명확하므로 추가 질문 없음
        summary_of_motivation=mock_summary
    )
    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.return_value = mock_llm_response
    mock_llm_instance = MagicMock()
    mock_llm_instance.with_structured_output.return_value = mock_structured_llm
    mocker.patch(
        'backend.app.graph_nodes.why.clarify_motivation_node.get_high_performance_llm',
        return_value=mock_llm_instance
    )
    # --- ---

    # --- Input State ---
    input_state: WhyGraphState = {
        "messages": [
            AIMessage(content="이 AI 회의록 도구를 통해 궁극적으로 달성하고 싶은 가장 중요한 목표는 무엇인가요?"),
            HumanMessage(content="매번 회의록 쓰는 데 시간이 너무 오래 걸려요. 그 시간을 아껴서 다른 중요한 일에 쓰고 싶습니다.")
        ],
        "session_id": "test-session-clear", "initial_topic": "AI 회의록 도구", "error_message": None,
        "idea_summary": "AI 기반 자동 회의록 작성 도구", "identified_what": "AI 기반 자동 회의록 작성 도구",
        "identified_how": None, "final_motivation_summary": None, "motivation_clear": False,
        "identified_assumptions": [], "probed_assumptions": [], "assumptions_fully_probed": False,
    }
    # --- ---

    # --- Execute Node ---
    result_state_update = await clarify_motivation_node(input_state)
    # --- ---

    # --- Assertions ---
    assert result_state_update is not None
    assert result_state_update.get("motivation_clear") is True
    assert result_state_update.get("final_motivation_summary") == mock_summary
    assert "messages" not in result_state_update # 메시지 업데이트 없음 확인
    assert result_state_update.get("error_message") is None
    mock_structured_llm.ainvoke.assert_called_once()
    # --- ---

# --- Test Case 2: Motivation is Unclear ---
async def test_clarify_motivation_when_unclear(mocker):
    """
    동기가 불명확하다고 판단될 때, 상태 업데이트가 올바른지 테스트
    (motivation_clear=False, messages에 추가 질문 포함)
    """
    # --- Mocking Setup ---
    mock_clarification_q = "말씀하신 '다른 중요한 일'이 구체적으로 어떤 종류의 업무를 의미하는지 좀 더 자세히 알 수 있을까요?"
    mock_llm_response = MotivationClarityOutput(
        is_motivation_clear=False,
        clarification_question=mock_clarification_q,
        summary_of_motivation=None
    )
    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.return_value = mock_llm_response
    mock_llm_instance = MagicMock()
    mock_llm_instance.with_structured_output.return_value = mock_structured_llm
    mocker.patch(
        'backend.app.graph_nodes.why.clarify_motivation_node.get_high_performance_llm',
        return_value=mock_llm_instance
    )
    # --- ---

    # --- Input State ---
    input_state: WhyGraphState = {
         "messages": [
            AIMessage(content="이 AI 회의록 도구를 통해 궁극적으로 달성하고 싶은 가장 중요한 목표는 무엇인가요?"),
            HumanMessage(content="매번 회의록 쓰는 데 시간이 너무 오래 걸려요. 그 시간을 아껴서 다른 중요한 일에 쓰고 싶습니다.")
        ],
        "session_id": "test-session-unclear", "initial_topic": "AI 회의록 도구", "error_message": None,
        "idea_summary": "AI 기반 자동 회의록 작성 도구", "identified_what": "AI 기반 자동 회의록 작성 도구",
        "identified_how": None, "final_motivation_summary": None, "motivation_clear": False,
        "identified_assumptions": [], "probed_assumptions": [], "assumptions_fully_probed": False,
    }
    # --- ---

    # --- Execute Node ---
    result_state_update = await clarify_motivation_node(input_state)
    # --- ---

    # --- Assertions ---
    assert result_state_update is not None
    assert result_state_update.get("motivation_clear") is False
    assert "final_motivation_summary" not in result_state_update or result_state_update.get("final_motivation_summary") is None
    assert "messages" in result_state_update
    assert len(result_state_update["messages"]) == 1
    new_message = result_state_update["messages"][0]
    assert isinstance(new_message, AIMessage)
    assert new_message.content == mock_clarification_q
    assert result_state_update.get("error_message") is None
    mock_structured_llm.ainvoke.assert_called_once()
    # --- ---

# --- Test Case 3: LLM Error ---
async def test_clarify_motivation_llm_error(mocker):
    """LLM 호출 오류 시 에러 상태 반환 테스트"""
    # --- Mocking Setup ---
    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.side_effect = Exception("LLM Error")
    mock_llm_instance = MagicMock()
    mock_llm_instance.with_structured_output.return_value = mock_structured_llm
    mocker.patch(
        'backend.app.graph_nodes.why.clarify_motivation_node.get_high_performance_llm',
        return_value=mock_llm_instance
    )
    # --- ---

    # --- Input State ---
    input_state: WhyGraphState = {
        "messages": [ AIMessage(content="Previous question"), HumanMessage(content="User answer") ],
        "session_id": "test-session-clarify-error", "initial_topic": "Test", "error_message": None,
        "idea_summary": "Test", "identified_what": None, "identified_how": None,
        "final_motivation_summary": None, "motivation_clear": False, "identified_assumptions": [],
        "probed_assumptions": [], "assumptions_fully_probed": False,
    }
    # --- ---

    # --- Execute Node ---
    result_state_update = await clarify_motivation_node(input_state)
    # --- ---

    # --- Assertions ---
    assert result_state_update is not None
    assert "error_message" in result_state_update
    assert result_state_update["error_message"] is not None
    assert "LLM 호출 오류" in result_state_update["error_message"]
    assert "messages" in result_state_update # 사용자에게 전달할 오류 메시지 포함 확인
    assert isinstance(result_state_update["messages"][0], AIMessage)
    assert "시스템 오류: 동기 명확화 처리 실패" in result_state_update["messages"][0].content
    # --- ---