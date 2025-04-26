# backend/tests/graph_nodes/why/test_understand_idea_node.py

import pytest
from unittest.mock import AsyncMock, MagicMock # 비동기 함수 및 객체 모킹

# 테스트 대상 함수 및 관련 클래스 임포트
from backend.app.graph_nodes.why.understand_idea_node import understand_idea_node, IdeaSummaryOutput
from backend.app.models.why_graph_state import WhyGraphState # 실제 정의된 WhyGraphState 임포트
from langchain_core.messages import HumanMessage

# pytest를 비동기 함수와 함께 사용하기 위해 مارک 설정
pytestmark = pytest.mark.asyncio

# 테스트 케이스 정의
async def test_understand_idea_success(mocker):
    """
    understand_idea_node가 성공적으로 아이디어를 요약하고 상태를 업데이트하는지 테스트
    """
    # --- Mocking Setup ---
    # 1. Mock LLM 응답 정의 (Pydantic 모델 객체)
    mock_llm_response = IdeaSummaryOutput(
        idea_summary="사용자는 AI 기반 자동 회의록 작성 도구를 만들고 싶어합니다.",
        identified_what="AI 기반 자동 회의록 작성 도구",
        identified_how="구체적인 방법은 언급되지 않음"
    )

    # 2. structured_llm 객체의 ainvoke 메소드를 모킹
    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.return_value = mock_llm_response

    # 3. get_fast_llm 함수가 모킹된 LLM 객체를 반환하도록 설정
    #    with_structured_output이 mock_structured_llm을 반환하도록 설정
    mock_llm_instance = MagicMock()
    mock_llm_instance.with_structured_output.return_value = mock_structured_llm
    mocker.patch(
        'backend.app.graph_nodes.why.understand_idea_node.get_fast_llm',
        return_value=mock_llm_instance
    )
    # --- ---

    # --- Input State ---
    initial_idea = "회의 내용을 자동으로 요약하고 정리해주는 AI 비서를 만들면 어떨까요?"
    input_state: WhyGraphState = {
        "messages": [HumanMessage(content=initial_idea)],
        # WhyGraphState의 다른 필드들은 기본값 사용
        "session_id": "test-session-123",
        "initial_topic": initial_idea,
        "error_message": None,
        "idea_summary": None,
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
    result_state_update = await understand_idea_node(input_state)
    # --- ---

    # --- Assertions ---
    # 반환된 상태 업데이트 확인
    assert result_state_update is not None
    assert result_state_update.get("idea_summary") == mock_llm_response.idea_summary
    assert result_state_update.get("identified_what") == mock_llm_response.identified_what
    assert result_state_update.get("identified_how") == mock_llm_response.identified_how
    assert result_state_update.get("error_message") is None

    # LLM 호출 확인 (선택적)
    mock_structured_llm.ainvoke.assert_called_once()
    # --- ---

async def test_understand_idea_no_user_message():
    """
    입력 상태의 마지막 메시지가 HumanMessage가 아닐 때 오류를 반환하는지 테스트
    """
    input_state: WhyGraphState = {
        "messages": [], # 메시지가 비어있는 경우
         # 나머지 필드 초기화 (test_understand_idea_success와 동일하게)
        "session_id": "test-session-empty",
        "initial_topic": None,
        "error_message": None,
        "idea_summary": None,
        "identified_what": None,
        "identified_how": None,
        "final_motivation_summary": None,
        "motivation_clear": False,
        "identified_assumptions": [],
        "probed_assumptions": [],
        "assumptions_fully_probed": False,
    }

    result_state_update = await understand_idea_node(input_state)

    assert result_state_update is not None
    assert "error_message" in result_state_update
    assert result_state_update["error_message"] is not None
    # 구체적인 오류 메시지 확인 가능
    # assert "입력 메시지가 비어있습니다" in result_state_update["error_message"]

async def test_understand_idea_llm_error(mocker):
    """
    LLM 호출 중 예외가 발생했을 때 오류 상태를 반환하는지 테스트
    """
    # --- Mocking Setup ---
    # ainvoke 호출 시 예외 발생 설정
    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.side_effect = Exception("LLM API Error")

    mock_llm_instance = MagicMock()
    mock_llm_instance.with_structured_output.return_value = mock_structured_llm
    mocker.patch(
        'backend.app.graph_nodes.why.understand_idea_node.get_fast_llm',
        return_value=mock_llm_instance
    )
    # --- ---

    # --- Input State ---
    input_state: WhyGraphState = {
        "messages": [HumanMessage(content="Test idea")],
        # 나머지 필드 초기화
        "session_id": "test-session-error",
        "initial_topic": "Test idea",
        "error_message": None,
        "idea_summary": None,
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
    result_state_update = await understand_idea_node(input_state)
    # --- ---

    # --- Assertions ---
    assert result_state_update is not None
    assert "error_message" in result_state_update
    assert result_state_update["error_message"] is not None
    assert "LLM 호출 오류" in result_state_update["error_message"]
    # --- ---