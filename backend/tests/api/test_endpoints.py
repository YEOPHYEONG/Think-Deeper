# backend/tests/api/test_endpoints.py

import pytest
from fastapi.testclient import TestClient

# FastAPI 앱 import: main.py에서 app 객체를 export한다고 가정합니다.
from backend.app.main import app

# 노드용 FakeLLM 준비
class FakeLLM:
    def __init__(self, outputs):
        self.outputs = outputs
        self.idx = 0
    def with_structured_output(self, model):
        fake = self
        class SL:
            async def ainvoke(self, messages):
                out = fake.outputs[fake.idx]
                fake.idx += 1
                return out
        return SL()

@pytest.fixture(autouse=True)
def patch_llm(monkeypatch):
    """
    모든 LLM 호출을 FakeLLM으로 대체.
    호출 순서:
     1) understand_idea_node
     2) ask_motivation_why_node
     3) clarify_motivation_node
     4) identify_assumptions_node
     5) probe_assumption_node (2번)
    """
    from backend.app.graph_nodes.why.understand_idea_node import IdeaSummaryOutput
    from backend.app.graph_nodes.why.ask_motivation_why_node import MotivationQuestionOutput
    from backend.app.graph_nodes.why.clarify_motivation_node import MotivationClarityOutput
    from backend.app.graph_nodes.why.identify_assumptions_node import IdentifiedAssumptionsOutput
    from backend.app.graph_nodes.why.probe_assumption_node import AssumptionQuestionOutput

    outputs = [
        IdeaSummaryOutput(
            idea_summary="앱은 목표 관리 지원",
            identified_what="목표 관리",
            identified_how="모바일 UI"
        ),
        MotivationQuestionOutput(motivation_question="왜 목표 관리가 중요하신가요?"),
        MotivationClarityOutput(
            is_motivation_clear=True,
            clarification_question=None,
            summary_of_motivation="지속적 성취 유도"
        ),
        IdentifiedAssumptionsOutput(identified_assumptions=[
            "사용자는 앱 사용법을 쉽게 배울 수 있다.",
            "데이터 보안이 철저히 유지된다."
        ]),
        AssumptionQuestionOutput(assumption_question="가정1 근거?"),
        AssumptionQuestionOutput(assumption_question="가정2 보장장치?")
    ]
    fake = FakeLLM(outputs)

    # Why 흐름 노드들 LLM 호출 패치
    monkeypatch.setattr(
        'backend.app.graph_nodes.why.understand_idea_node.get_fast_llm',
        lambda: fake
    )
    monkeypatch.setattr(
        'backend.app.graph_nodes.why.ask_motivation_why_node.get_high_performance_llm',
        lambda: fake
    )
    monkeypatch.setattr(
        'backend.app.graph_nodes.why.clarify_motivation_node.get_high_performance_llm',
        lambda: fake
    )
    monkeypatch.setattr(
        'backend.app.graph_nodes.why.identify_assumptions_node.get_high_performance_llm',
        lambda: fake
    )
    monkeypatch.setattr(
        'backend.app.graph_nodes.why.probe_assumption_node.get_high_performance_llm',
        lambda: fake
    )

@pytest.fixture
def client():
    return TestClient(app)


def test_session_and_chat_flow(client):
    # 1) 세션 생성
    res = client.post("/api/v1/sessions", json={"topic": "테스트 주제", "initial_agent_type": "critic"})
    assert res.status_code == 201
    session_id = res.json()["session_id"]

    # 2) 메인 채팅 엔드포인트 (Critic) 호출
    chat_res = client.post(f"/api/v1/sessions/{session_id}/message", json={"content": "Hello"})
    assert chat_res.status_code == 200
    data = chat_res.json()
    assert data.get("role") == "assistant"
    assert isinstance(data.get("content"), str)


def test_why_explore_endpoint(client):
    # 1) 새로운 세션 생성
    res = client.post("/api/v1/sessions", json={"topic": "아이디어", "initial_agent_type": "critic"})
    assert res.status_code == 201
    session_id = res.json()["session_id"]

    # 2) Why 흐름 시작: 초기 아이디어 전송
    res1 = client.post(
        f"/api/v1/sessions/{session_id}/explore-why",
        json={"initial_idea": "이 앱으로 목표를 관리하고 싶습니다."}
    )
    assert res1.status_code == 200
    first_q = res1.json().get("content", "")
    assert "왜 목표 관리가 중요하신가요?" in first_q

    # 3) Why 흐름 계속: 모의 사용자 답변 전송 (clarify bypass)
    res2 = client.post(
        f"/api/v1/sessions/{session_id}/explore-why",
        json={"initial_idea": "목표가 성취감을 줍니다."}
    )
    assert res2.status_code == 200
    final_msg = res2.json().get("content", "")
    assert "모든 주요 가정을 살펴본 것 같습니다" in final_msg
