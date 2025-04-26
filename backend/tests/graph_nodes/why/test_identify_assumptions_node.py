# backend/tests/graph_nodes/why/test_identify_assumptions_node.py

import pytest
from unittest.mock import AsyncMock, MagicMock

# 테스트 대상 함수 및 관련 클래스 임포트
from backend.app.graph_nodes.why.identify_assumptions_node import identify_assumptions_node, IdentifiedAssumptionsOutput
# from backend.app.models.why_graph_state import WhyGraphState # 실제 정의된 WhyGraphState 임포트 가정
from backend.app.models.graph_state import GraphState as WhyGraphState # 임시 (실제 정의된 것으로 교체 필요)
from langchain_core.messages import AIMessage, HumanMessage # 필요시 사용

pytestmark = pytest.mark.asyncio

# 테스트 케이스 정의
async def test_identify_assumptions_success(mocker):
    """
    identify_assumptions_node가 성공적으로 가정을 식별하고 중요도 순으로 정렬하여
    상태를 업데이트하는지 테스트
    """
    # --- Mocking Setup ---
    # 1. Mock LLM 응답 정의 (중요도 순으로 정렬된 가정 리스트)
    mock_sorted_assumptions = [
        "사용자는 이 앱 사용법을 쉽게 배울 수 있다.", # 가장 중요 가정
        "유사한 경쟁 서비스가 빠르게 나타나지 않을 것이다.",
        "개발 및 운영에 필요한 충분한 데이터를 확보할 수 있다."
    ]
    mock_llm_response = IdentifiedAssumptionsOutput(
        identified_assumptions=mock_sorted_assumptions
    )

    # 2. structured_llm 객체의 ainvoke 메소드를 모킹
    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.return_value = mock_llm_response

    # 3. get_high_performance_llm 함수 모킹 설정
    mock_llm_instance = MagicMock()
    mock_llm_instance.with_structured_output.return_value = mock_structured_llm
    mocker.patch(
        'backend.app.graph_nodes.why.identify_assumptions_node.get_high_performance_llm',
        return_value=mock_llm_instance
    )
    # --- ---

    # --- Input State ---
    # 이 노드는 idea_summary와 final_motivation_summary가 상태에 있어야 함
    input_state: WhyGraphState = {
        "messages": [
            # ... 이전 대화 기록 ...
            AIMessage(content="<동기 명확화 완료 메시지 - 실제로는 없음>"), # 예시
            HumanMessage(content="<동기 명확화 완료 후 사용자 응답 - 실제로는 없음>")
        ],
        "session_id": "test-session-identify",
        "initial_topic": "AI 회의록 도구",
        "error_message": None,
        "idea_summary": "AI 기반 자동 회의록 작성 도구",
        "identified_what": "AI 기반 자동 회의록 작성 도구",
        "identified_how": None,
        "final_motivation_summary": "사용자는 회의록 작성 시간을 줄여 핵심 업무에 집중하고 싶어합니다.", # 명확화된 동기
        "motivation_clear": True, # 동기가 명확해진 상태
        "identified_assumptions": [], # 초기값
        "probed_assumptions": [], # 초기값
        "assumptions_fully_probed": False,
    }
    # --- ---

    # --- Execute Node ---
    result_state_update = await identify_assumptions_node(input_state)
    # --- ---

    # --- Assertions ---
    assert result_state_update is not None
    # 식별 및 정렬된 가정 리스트 확인
    assert "identified_assumptions" in result_state_update
    assert result_state_update["identified_assumptions"] == mock_sorted_assumptions
    # probed_assumptions 리스트가 빈 리스트로 초기화되었는지 확인
    assert "probed_assumptions" in result_state_update
    assert result_state_update["probed_assumptions"] == []
    assert result_state_update.get("error_message") is None

    # LLM 호출 확인
    mock_structured_llm.ainvoke.assert_called_once()
    # --- ---

async def test_identify_assumptions_missing_input():
    """
    입력 상태에 idea_summary 또는 final_motivation_summary가 없을 때 오류 반환 테스트
    """
    # Case 1: final_motivation_summary 누락
    input_state_no_motivation: WhyGraphState = {
        "messages": [], "session_id": "test-session-id-1", "initial_topic": "Test",
        "error_message": None, "idea_summary": "Test idea", "identified_what": None,
        "identified_how": None, "final_motivation_summary": None, # 누락
        "motivation_clear": True, "identified_assumptions": [], "probed_assumptions": [],
        "assumptions_fully_probed": False,
    }
    result1 = await identify_assumptions_node(input_state_no_motivation)
    assert result1 is not None
    assert "error_message" in result1 and result1["error_message"] is not None
    assert "final_motivation_summary" in result1["error_message"]

    # Case 2: idea_summary 누락
    input_state_no_idea: WhyGraphState = {
         "messages": [], "session_id": "test-session-id-2", "initial_topic": "Test",
        "error_message": None, "idea_summary": None, # 누락
        "identified_what": None, "identified_how": None,
        "final_motivation_summary": "Motivation summary",
        "motivation_clear": True, "identified_assumptions": [], "probed_assumptions": [],
        "assumptions_fully_probed": False,
    }
    result2 = await identify_assumptions_node(input_state_no_idea)
    assert result2 is not None
    assert "error_message" in result2 and result2["error_message"] is not None
    assert "idea_summary" in result2["error_message"]

async def test_identify_assumptions_llm_error(mocker):
    """LLM 호출 오류 시 에러 상태 반환 테스트"""
    # --- Mocking Setup ---
    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.side_effect = Exception("LLM Error for identification")
    mock_llm_instance = MagicMock()
    mock_llm_instance.with_structured_output.return_value = mock_structured_llm
    mocker.patch(
        'backend.app.graph_nodes.why.identify_assumptions_node.get_high_performance_llm',
        return_value=mock_llm_instance
    )
    # --- ---

    # --- Input State ---
    input_state: WhyGraphState = {
        "messages": [], "session_id": "test-session-identify-error", "initial_topic": "Test",
        "error_message": None, "idea_summary": "Test idea", "identified_what": None,
        "identified_how": None, "final_motivation_summary": "Motivation summary",
        "motivation_clear": True, "identified_assumptions": [], "probed_assumptions": [],
        "assumptions_fully_probed": False,
    }
    # --- ---

    # --- Execute Node ---
    result_state_update = await identify_assumptions_node(input_state)
    # --- ---

    # --- Assertions ---
    assert result_state_update is not None
    assert "error_message" in result_state_update
    assert result_state_update["error_message"] is not None
    assert "LLM 호출 오류" in result_state_update["error_message"]
    # 이 노드는 오류 발생 시 messages를 업데이트하지 않음
    assert "identified_assumptions" not in result_state_update or result_state_update["identified_assumptions"] == []
    # --- ---