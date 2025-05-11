# backend/app/graph_nodes/why/motivation_elicitation_node.py

from typing import Dict, Any, List, Optional, Union
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langgraph.types import interrupt # interrupt 임포트
from pydantic import BaseModel, Field # Pydantic 모델 사용
import json

from ...core.llm_provider import get_high_performance_llm
from ...models.why_graph_state import WhyGraphState # 타입 힌팅용

class MotivationClarityOutput(BaseModel):
    is_motivation_clear: bool = Field(..., description="동기 명확 여부")
    clarification_question: Optional[str] = Field(None, description="불명확 시 추가 질문 또는 첫 질문")
    summary_of_motivation: Optional[str] = Field(None, description="명확 시 반환할 요약")

async def motivation_elicitation_node(state: Dict[str, Any]) -> Union[Dict[str, Any], None]:
    """
    Motivation Elicitation 노드:
    대화 이력을 기반으로 사용자의 동기 명확성을 판단하고,
    - 동기가 불명확하면 (첫 질문 포함) 추가 질문을 생성하여 interrupt 발생
    - 동기가 명확하면 요약을 생성하여 다음 노드로 상태 반환
    """
    print("[MOTIV][NODE_LIFECYCLE] Entering motivation_elicitation_node")

    messages: List[Union[BaseMessage, dict]] = state.get('messages', [])
    raw_topic: Optional[str] = state.get('raw_topic')
    raw_idea: Optional[str] = state.get('raw_idea')
    # has_asked_initial 플래그는 이제 이 노드에서 직접 사용하지 않고,
    # LLM이 대화 기록(messages)을 보고 첫 질문인지 후속 질문인지 판단하도록 유도합니다.
    # 다만, 오케스트레이터에서 이 플래그를 관리할 수 있도록 interrupt 데이터에는 포함합니다.

    llm = get_high_performance_llm()
    structured_llm = llm.with_structured_output(MotivationClarityOutput)

    # 대화 기록을 시스템 프롬프트에서 유저 프롬프트로 이동
    system_prompt = """
    # 역할: 당신은 사용자의 동기 설명을 분석하고 명확성을 판단하는 Why agent입니다. 
    목표는 사용자가 자신의 핵심 동기('Why')를 충분히 깊고 명확하게 이해했는지 평가하고, 그렇지 않다면 더 깊은 성찰을 유도하는 추가 질문을 던지는 것입니다.


# 핵심 지침:
1.  **명확성 평가:** 사용자의 답변이 아이디어의 근본적인 'Why'(궁극적 목적, 핵심 가치, 해결하려는 진짜 문제 등)를 구체적이고 설득력 있게 설명하는지 평가하세요. 피상적이거나 모호한 답변은 '불명확'으로 판단합니다.
2.  **판단 기준:**
    * **명확 (Clear - is_motivation_clear=True):
    ** 사용자가 자신의 핵심 동기를 구체적인 용어로 설명하고, 그것이 왜 중요한지에 대한 논리적인 이유를 제시하며, 아이디어와의 연결성이 분명합니다. 다음 단계(가정 탐색)로 넘어가도 좋습니다.
    * **불명확 (Unclear - is_motivation_clear=False):
    ** 답변이 추상적이거나, 동문서답이거나, 여러 동기가 혼재되어 핵심을 파악하기 어렵거나, 논리적 근거가 부족합니다. 추가 질문이 필요합니다.
3.  **추가 질문 생성 (불명확 시):
    ** 만약 동기가 불명확하다면, 사용자의 답변 내용 중 **가장 불명확하거나 더 깊이 탐색해야 할 부분**을 정확히 짚어내는 **단 하나의 구체적이고 통찰력 있는 후속 질문**을 생성하세요. 막연히 "더 자세히 설명해주세요"라고 하지 마세요. (예: "말씀하신 '성장'이 구체적으로 어떤 종류의 성장을 의미하는지 더 설명해주실 수 있나요?", "그 목표가 아이디어의 [특정 측면]과 어떻게 직접적으로 연결되는지 궁금합니다.")

각 응답에서 다음을 포함해야 합니다:
- is_motivation_clear: 동기가 충분히 명확한지 여부 (true/false)
- clarification_question: 동기가 명확하지 않은 경우, 더 깊은 이해를 위한 질문
- summary_of_motivation: 동기가 명확한 경우, 요약된 동기 설명

응답은 반드시 JSON 형식이어야 하며, 위의 세 필드를 모두 포함해야 합니다."""

    # 대화 기록 포맷팅
    history_lines = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            history_lines.append(f"- User: {msg.content}")
        elif isinstance(msg, AIMessage):
            history_lines.append(f"- Assistant: {msg.content}")
        elif isinstance(msg, dict):
            msg_type = msg.get("type")
            content = msg.get("content")
            if content is not None:
                if msg_type == "human":
                    history_lines.append(f"- User: {content}")
                elif msg_type == "ai" or msg_type == "assistant":
                    history_lines.append(f"- Assistant: {content}")

    formatted_history = "\n".join(history_lines) if history_lines else f"Initial Idea/Topic: {raw_idea or raw_topic or 'Not provided'}"

    # 대화 기록을 유저 프롬프트로 이동
    user_prompt = f"""Dialogue History:
{formatted_history}

이 대화를 바탕으로 사용자의 동기가 충분히 명확한지 평가하고, 필요한 경우 추가 질문을 하거나 동기를 요약해주세요."""

    print(f"  [MOTIV][DEBUG] user_prompt to LLM:\n{user_prompt}")
    print(f"  [MOTIV][INFO] Calling LLM for motivation clarity/question...")
    
    # LLM 호출
    resp = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)])
    print(f"  [MOTIV][DEBUG] LLM response (resp): {resp}")
    print(f"  [MOTIV][INFO] LLM call completed.")

    # 응답 파싱
    try:
        content = resp.content
        # 마크다운 코드 블록 제거
        if content.startswith("```json"):
            content = content[7:]  # ```json 제거
        if content.endswith("```"):
            content = content[:-3]  # ``` 제거
        content = content.strip()
        
        resp_dict = json.loads(content)
        is_motivation_clear = resp_dict.get("is_motivation_clear", False)
        clarification_question = resp_dict.get("clarification_question", "")
        summary_of_motivation = resp_dict.get("summary_of_motivation", "")
    except json.JSONDecodeError as e:
        print(f"  [MOTIV][ERROR] Failed to parse LLM response as JSON: {resp.content}")
        print(f"  [MOTIV][ERROR] JSON decode error: {str(e)}")
        is_motivation_clear = False
        clarification_question = "죄송합니다. 응답을 처리하는 중에 문제가 발생했습니다. 다시 한번 설명해주시겠어요?"
        summary_of_motivation = None

    # AI의 응답을 messages에 추가
    messages.append(AIMessage(content=clarification_question if not is_motivation_clear else summary_of_motivation))

    if not is_motivation_clear:
        print(f"  [MOTIV][DEBUG] Motivation unclear or first question -> raising interrupt with question: {clarification_question}")
        interrupt_data_for_question = {
            "messages": messages,  # AI의 응답이 포함된 messages
            "has_asked_initial": True,
            "clarification_question": clarification_question,
            "user_facing_message": clarification_question
        }
        print(f"  [MOTIV][DEBUG] Data for question interrupt (interrupt_data_for_question):")
        print(f"    - messages (last 2): {[m.content for m in messages[-2:]]}")
        print(f"    - has_asked_initial: {interrupt_data_for_question['has_asked_initial']}")
        print(f"    - clarification_question: {interrupt_data_for_question['clarification_question']}")
        raise interrupt(value=interrupt_data_for_question)
    else:
        summary_msg_str = summary_of_motivation or "(동기 요약 정보 없음)"
        print(f"  [MOTIV][DEBUG] Motivation clear -> returning summary state: {summary_msg_str}")
        
        updated_messages_with_summary = messages + [AIMessage(content=summary_msg_str)]

        state_update_on_clear = {
            "messages": updated_messages_with_summary, # AI 요약이 포함된 전체 메시지 리스트
            "motivation_cleared": True,
            "final_motivation_summary": summary_msg_str,
            "has_asked_initial": True, 
            "error_message": None,
            "clarification_question": None
        }
        # --- 추가된 로그 ---
        print(f"  [MOTIV][DEBUG] Data for state_update_on_clear:")
        print(f"    - messages (last 2): {[m.content if isinstance(m, BaseMessage) else m for m in updated_messages_with_summary[-2:]]}")
        print(f"    - has_asked_initial: {state_update_on_clear.get('has_asked_initial')}")
        print(f"    - motivation_cleared: {state_update_on_clear.get('motivation_cleared')}")
        # --- ---
        print(f"[MOTIV][NODE_LIFECYCLE] Exiting motivation_elicitation_node with state update.")
        return state_update_on_clear
