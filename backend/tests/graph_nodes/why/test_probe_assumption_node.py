# backend/tests/graph_nodes/why/test_probe_assumption_node.py

import pytest
from unittest.mock import AsyncMock, MagicMock

# 테스트 대상 함수 및 관련 클래스 임포트
from backend.app.graph_nodes.why.probe_assumption_node import probe_assumption_node, AssumptionQuestionOutput
# from backend.app.models.why_graph_state import WhyGraphState # 실제 정의된 WhyGraphState 임포트 가정
from backend.app.models.graph_state import GraphState as WhyGraphState # 임시 (실제 정의된 것으로 교체 필요)
from langchain_core.messages import AIMessage, HumanMessage

pytestmark = pytest.mark.asyncio

# --- Test Case 1: Probe the first (highest priority) assumption ---
async def test_probe_first_assumption(mocker):
    """첫 번째 (가장 중요한) 미탐색 가정을 질문하는지 테스트"""
    # --- Mocking Setup ---
    mock_question = "가정 '사용자는 이 앱 사용법을 쉽게 배울 수 있다.'에 대한 구체적인 근거는 무엇인가요?"
    mock_llm_response = AssumptionQuestionOutput(assumption_question=mock_question)
    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.return_value = mock_llm_response
    mock_llm_instance = MagicMock()
    mock_llm_instance.with_structured_output.return_value = mock_structured_llm
    mocker.patch(
        'backend.app.graph_nodes.why.probe_assumption_node.get_high_performance_llm',
        return_value=mock_llm_instance
    )
    # --- ---

    # --- Input State ---
    sorted_assumptions = [
        "사용자는 이 앱 사용법을 쉽게 배울 수 있다.", # Probe 대상
        "경쟁 서비스가 빠르게 나타나지 않을 것이다."
    ]
    input_state: WhyGraphState = {
        "messages": [ HumanMessage(content="<User answer to motivation question>") ],
        "session_id": "test-probe-1", "initial_topic": "Test", "error_message": None,
        "idea_summary": "Test", "identified_what": None, "identified_how": None,
        "final_motivation_summary": "Motivation", "motivation_clear": True,
        "identified_assumptions": sorted_assumptions,
        "probed_assumptions": [], # 아직 탐색된 가정 없음
        "assumptions_fully_probed": False,
    }
    # --- ---

    # --- Execute Node ---
    result_state_update = await probe_assumption_node(input_state)
    # --- ---

    # --- Assertions ---
    assert result_state_update is not None
    assert "messages" in result_state_update
    assert len(result_state_update["messages"]) == 1
    new_message = result_state_update["messages"][0]
    assert isinstance(new_message, AIMessage)
    assert new_message.content == mock_question # 생성된 질문 확인
    assert "probed_assumptions" in result_state_update
    # 첫 번째 가정이 probed_assumptions에 추가되었는지 확인
    assert result_state_update["probed_assumptions"] == [sorted_assumptions[0]]
    assert result_state_update.get("assumptions_fully_probed") is False # 아직 완료 아님
    assert result_state_update.get("error_message") is None
    mock_structured_llm.ainvoke.assert_called_once()
    # --- ---

# --- Test Case 2: Probe the second assumption (first one already probed) ---
async def test_probe_second_assumption(mocker):
    """이미 탐색된 가정을 건너뛰고 다음 미탐색 가정을 질문하는지 테스트"""
    # --- Mocking Setup ---
    mock_question = "가정 '경쟁 서비스가 빠르게 나타나지 않을 것이다.'는 어떤 근거로 판단하셨나요?"
    mock_llm_response = AssumptionQuestionOutput(assumption_question=mock_question)
    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.return_value = mock_llm_response
    mock_llm_instance = MagicMock()
    mock_llm_instance.with_structured_output.return_value = mock_structured_llm
    mocker.patch(
        'backend.app.graph_nodes.why.probe_assumption_node.get_high_performance_llm',
        return_value=mock_llm_instance
    )
    # --- ---

    # --- Input State ---
    sorted_assumptions = [
        "사용자는 이 앱 사용법을 쉽게 배울 수 있다.", # 이미 탐색됨
        "경쟁 서비스가 빠르게 나타나지 않을 것이다."  # Probe 대상
    ]
    input_state: WhyGraphState = {
        "messages": [ HumanMessage(content="<Answer to first assumption question>") ],
        "session_id": "test-probe-2", "initial_topic": "Test", "error_message": None,
        "idea_summary": "Test", "identified_what": None, "identified_how": None,
        "final_motivation_summary": "Motivation", "motivation_clear": True,
        "identified_assumptions": sorted_assumptions,
        "probed_assumptions": [sorted_assumptions[0]], # 첫 번째 가정은 이미 탐색됨
        "assumptions_fully_probed": False,
    }
    # --- ---

    # --- Execute Node ---
    result_state_update = await probe_assumption_node(input_state)
    # --- ---

    # --- Assertions ---
    assert result_state_update is not None
    assert "messages" in result_state_update
    assert len(result_state_update["messages"]) == 1
    new_message = result_state_update["messages"][0]
    assert isinstance(new_message, AIMessage)
    assert new_message.content == mock_question # 두 번째 가정에 대한 질문 확인
    assert "probed_assumptions" in result_state_update
    # 두 번째 가정이 probed_assumptions에 추가되었는지 확인
    assert result_state_update["probed_assumptions"] == sorted_assumptions # 이제 둘 다 포함
    assert result_state_update.get("assumptions_fully_probed") is False
    assert result_state_update.get("error_message") is None
    mock_structured_llm.ainvoke.assert_called_once()
    # --- ---

# --- Test Case 3: All assumptions probed ---
async def test_probe_all_assumptions_probed(mocker):
    """모든 가정이 이미 탐색되었을 때 종료 상태를 반환하는지 테스트"""
    # --- Mocking Setup (LLM 호출 안되어야 함) ---
    mock_structured_llm = AsyncMock()
    mock_llm_instance = MagicMock()
    mock_llm_instance.with_structured_output.return_value = mock_structured_llm
    mocker.patch(
        'backend.app.graph_nodes.why.probe_assumption_node.get_high_performance_llm',
        return_value=mock_llm_instance
    )
    # --- ---

    # --- Input State ---
    sorted_assumptions = [
        "가정 A",
        "가정 B"
    ]
    input_state: WhyGraphState = {
        "messages": [ HumanMessage(content="<Answer to last assumption question>") ],
        "session_id": "test-probe-end", "initial_topic": "Test", "error_message": None,
        "idea_summary": "Test", "identified_what": None, "identified_how": None,
        "final_motivation_summary": "Motivation", "motivation_clear": True,
        "identified_assumptions": sorted_assumptions,
        "probed_assumptions": sorted_assumptions[:], # 모든 가정이 이미 탐색됨 (리스트 복사)
        "assumptions_fully_probed": False, # 아직 False 상태
    }
    # --- ---

    # --- Execute Node ---
    result_state_update = await probe_assumption_node(input_state)
    # --- ---

    # --- Assertions ---
    assert result_state_update is not None
    assert result_state_update.get("assumptions_fully_probed") is True # 종료 플래그 확인
    assert "messages" not in result_state_update # 추가 질문 없어야 함
    assert result_state_update.get("error_message") is None
    mock_structured_llm.ainvoke.assert_not_called() # LLM 호출 안했는지 확인
    # --- ---

# --- Test Case 4: LLM Error ---
async def test_probe_assumption_llm_error(mocker):
    """LLM 호출 오류 시 에러 상태 반환 테스트"""
    # --- Mocking Setup ---
    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.side_effect = Exception("LLM Error during probe")
    mock_llm_instance = MagicMock()
    mock_llm_instance.with_structured_output.return_value = mock_structured_llm
    mocker.patch(
        'backend.app.graph_nodes.why.probe_assumption_node.get_high_performance_llm',
        return_value=mock_llm_instance
    )
    # --- ---

    # --- Input State ---
    sorted_assumptions = ["가정 1"]
    input_state: WhyGraphState = {
        "messages": [ HumanMessage(content="<User answer>") ],
        "session_id": "test-probe-llm-error", "initial_topic": "Test", "error_message": None,
        "idea_summary": "Test", "identified_what": None, "identified_how": None,
        "final_motivation_summary": "Motivation", "motivation_clear": True,
        "identified_assumptions": sorted_assumptions,
        "probed_assumptions": [], # 아직 탐색 안함
        "assumptions_fully_probed": False,
    }
    # --- ---

    # --- Execute Node ---
    result_state_update = await probe_assumption_node(input_state)
    # --- ---

    # --- Assertions ---
    assert result_state_update is not None
    assert "error_message" in result_state_update
    assert result_state_update["error_message"] is not None
    assert "LLM 호출 오류" in result_state_update["error_message"]
    assert "messages" in result_state_update # 사용자 오류 메시지 확인
    assert isinstance(result_state_update["messages"][0], AIMessage)
    assert "가정 탐색 질문 생성에 실패" in result_state_update["messages"][0].content
    # 오류 발생 시 probed_assumptions는 업데이트되지 않아야 함
    assert result_state_update.get("probed_assumptions") == []
    # --- ---