# backend/tests/graph_nodes/why/test_ask_motivation_why_node.py

import pytest
from unittest.mock import AsyncMock, MagicMock

# 테스트 대상 함수 및 관련 클래스 임포트
from backend.app.graph_nodes.why.ask_motivation_why_node import ask_motivation_why_node, MotivationQuestionOutput
from backend.app.models.why_graph_state import WhyGraphState # 실제 정의된 WhyGraphState 임포트
from langchain_core.messages import AIMessage, HumanMessage # HumanMessage는 입력 상태용

# pytest를 비동기 함수와 함께 사용하기 위해 مارک 설정
pytestmark = pytest.mark.asyncio

# 테스트 케이스 정의
async def test_ask_motivation_success(mocker):
    """
    ask_motivation_why_node가 아이디어 요약을 바탕으로 성공적으로 동기 질문을 생성하고
    메시지 리스트를 업데이트하는지 테스트
    """
    # --- Mocking Setup ---
    # 1. Mock LLM 응답 정의
    mock_question = "이 AI 회의록 도구를 통해 궁극적으로 달성하고 싶은 가장 중요한 목표는 무엇인가요?"
    mock_llm_response = MotivationQuestionOutput(motivation_question=mock_question)

    # 2. structured_llm 객체의 ainvoke 메소드를 모킹
    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.return_value = mock_llm_response

    # 3. get_high_performance_llm 함수 모킹 설정
    mock_llm_instance = MagicMock()
    mock_llm_instance.with_structured_output.return_value = mock_structured_llm
    mocker.patch(
        'backend.app.graph_nodes.why.ask_motivation_why_node.get_high_performance_llm',
        return_value=mock_llm_instance
    )
    # --- ---

    # --- Input State ---
    # 이 노드는 idea_summary가 상태에 있어야 함
    input_state: WhyGraphState = {
        "messages": [HumanMessage(content="회의 내용을 자동으로 요약하는 AI 비서")], # 이전 메시지 기록
        "session_id": "test-session-ask",
        "initial_topic": "회의 내용을 자동으로 요약하는 AI 비서",
        "error_message": None,
        "idea_summary": "사용자는 AI 기반 자동 회의록 작성 도구를 만들고 싶어합니다.", # 이전 노드의 결과
        "identified_what": "AI 기반 자동 회의록 작성 도구",
        "identified_how": None,
        "final_motivation_summary": None,
        "motivation_clear": False,
        "identified_assumptions": [],
        "probed_assumptions": [],
        "assumptions_fully_probed": False,
    }
    # --- ---

    # --- Execute Node ---
    result_state_update = await ask_motivation_why_node(input_state)
    # --- ---

    # --- Assertions ---
    assert result_state_update is not None
    # 이 노드는 메시지 리스트를 업데이트해야 함
    assert "messages" in result_state_update
    assert len(result_state_update["messages"]) == 1 # 새 AIMessage 하나만 반환
    new_message = result_state_update["messages"][0]
    assert isinstance(new_message, AIMessage)
    assert new_message.content == mock_question # 모킹된 질문과 일치하는지 확인
    assert result_state_update.get("error_message") is None

    # LLM 호출 확인
    mock_structured_llm.ainvoke.assert_called_once()
    # --- ---

async def test_ask_motivation_missing_summary():
    """
    입력 상태에 idea_summary가 없을 때 오류를 반환하는지 테스트
    """
    input_state: WhyGraphState = {
        "messages": [HumanMessage(content="회의 내용을 자동으로 요약하는 AI 비서")],
        "session_id": "test-session-no-summary",
        "initial_topic": "회의 내용을 자동으로 요약하는 AI 비서",
        "error_message": None,
        "idea_summary": None, # 아이디어 요약 누락
        "identified_what": None,
        "identified_how": None,
        "final_motivation_summary": None,
        "motivation_clear": False,
        "identified_assumptions": [],
        "probed_assumptions": [],
        "assumptions_fully_probed": False,
    }

    result_state_update = await ask_motivation_why_node(input_state)

    assert result_state_update is not None
    assert "error_message" in result_state_update
    assert result_state_update["error_message"] is not None
    assert "idea_summary" in result_state_update["error_message"] # 오류 메시지 내용 확인

async def test_ask_motivation_llm_error(mocker):
    """
    LLM 호출 중 예외 발생 시 오류 상태와 사용자용 오류 메시지를 반환하는지 테스트
    """
    # --- Mocking Setup ---
    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.side_effect = Exception("LLM Connection Error")

    mock_llm_instance = MagicMock()
    mock_llm_instance.with_structured_output.return_value = mock_structured_llm
    mocker.patch(
        'backend.app.graph_nodes.why.ask_motivation_why_node.get_high_performance_llm',
        return_value=mock_llm_instance
    )
    # --- ---

    # --- Input State ---
    input_state: WhyGraphState = {
        "messages": [HumanMessage(content="Test idea")],
        "session_id": "test-session-ask-error",
        "initial_topic": "Test idea",
        "error_message": None,
        "idea_summary": "Test idea summary", # 아이디어 요약 필요
        "identified_what": None,
        "identified_how": None,
        "final_motivation_summary": None,
        "motivation_clear": False,
        "identified_assumptions": [],
        "probed_assumptions": [],
        "assumptions_fully_probed": False,
    }
    # --- ---

    # --- Execute Node ---
    result_state_update = await ask_motivation_why_node(input_state)
    # --- ---

    # --- Assertions ---
    assert result_state_update is not None
    assert "error_message" in result_state_update
    assert result_state_update["error_message"] is not None
    assert "LLM 호출 오류" in result_state_update["error_message"]
    # 사용자에게 전달될 오류 메시지도 확인
    assert "messages" in result_state_update
    assert len(result_state_update["messages"]) == 1
    assert isinstance(result_state_update["messages"][0], AIMessage)
    assert "시스템 오류: 동기 질문 생성에 실패했습니다" in result_state_update["messages"][0].content
    # --- ---