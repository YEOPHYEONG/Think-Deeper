# backend/tests/graph_nodes/why/test_why_flow_integration.py

import pytest

from backend.app.core.why_orchestration import run_why_exploration_turn
from backend.app.graph_nodes.why.understand_idea_node import IdeaSummaryOutput
from backend.app.graph_nodes.why.ask_motivation_why_node import MotivationQuestionOutput
from backend.app.graph_nodes.why.clarify_motivation_node import MotivationClarityOutput
from backend.app.graph_nodes.why.identify_assumptions_node import IdentifiedAssumptionsOutput
from backend.app.graph_nodes.why.probe_assumption_node import AssumptionQuestionOutput

@pytest.mark.asyncio
async def test_full_why_flow(monkeypatch):
    """
    아이디어 제시부터 모든 가정 탐색 종료까지,
    run_why_exploration_turn이 올바른 최종 메시지를 반환하는지 확인합니다.
    """

    # 1) 각 노드별로 반환할 모의 응답들 준비
    idea_summary = "이 앱은 사용자가 손쉽게 목표를 관리하도록 돕습니다."
    identified_what = "목표 관리"
    identified_how = "모바일 UI를 통해"
    motivation_q = "왜 목표 관리를 더 쉽게 만들고 싶으신가요?"
    clarity_out = MotivationClarityOutput(
        is_motivation_clear=True,
        clarification_question=None,
        summary_of_motivation="사용자가 지속적으로 목표를 달성하도록 돕기 위해"
    )
    assumptions = ["사용자는 이 앱 사용법을 쉽게 배울 수 있다.",
                   "데이터 보안이 철저히 유지된다."]
    probe_q1 = "가정 '사용자는 이 앱 사용법을 쉽게 배울 수 있다.'에 대해 어떤 근거가 있나요?"
    probe_q2 = "가정 '데이터 보안이 철저히 유지된다.'에 대해 어떤 보장 장치가 있나요?"

    # 2) FakeLLM 정의: 순서대로 위 모의 응답을 돌려줌
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

    outputs = [
        # understand_idea_node
        IdeaSummaryOutput(
            idea_summary=idea_summary,
            identified_what=identified_what,
            identified_how=identified_how
        ),
        # ask_motivation_why_node
        MotivationQuestionOutput(motivation_question=motivation_q),
        # clarify_motivation_node
        clarity_out,
        # identify_assumptions_node
        IdentifiedAssumptionsOutput(identified_assumptions=assumptions),
        # probe_assumption_node (첫 번째)
        AssumptionQuestionOutput(assumption_question=probe_q1),
        # probe_assumption_node (두 번째)
        AssumptionQuestionOutput(assumption_question=probe_q2),
    ]

    fake = FakeLLM(outputs)

    # 3) llm_provider의 두 함수 모두 FakeLLM을 리턴하도록 패치
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

    # 4) 통합 실행: 한 번의 호출로 전체 플로우를 타고 최종 메시지 반환
    resp = await run_why_exploration_turn(
        session_id="integration-test",
        user_input="이 앱으로 목표를 관리하고자 합니다.",
        initial_topic="이 앱으로 목표를 관리하고자 합니다."
    )

    # 5) 끝났을 때 Graph가 반환하는 마무리 문구 검증
    assert isinstance(resp, str)
    assert "모든 주요 가정을 살펴본 것 같습니다" in resp
