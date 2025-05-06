# backend/app/graph_nodes/why/motivation_elicitation_node.py

from typing import Dict, Any, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
# from langgraph.types import interrupt # Interrupt 사용 안 함
from pydantic import BaseModel, Field

from ...core.llm_provider import get_high_performance_llm
from ...models.why_graph_state import WhyGraphState

class MotivationClarityOutput(BaseModel):
    is_motivation_clear: bool = Field(..., description="동기 명확 여부")
    clarification_question: Optional[str] = Field(None, description="불명확 시 추가 질문")
    summary_of_motivation: Optional[str] = Field(None, description="명확 시 반환할 요약")

async def motivation_elicitation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Motivation Elicitation 노드:
    1) 첫 호출 시 Topic과 Idea 기반으로 '왜?' 질문 생성
    2) 이후에는 'messages' 채널의 대화 이력을 기반으로 동기 명확성 판단 및 후속 질문 또는 요약 반환
    3) 상태 업데이트 딕셔너리를 직접 반환
    """
    print("[MOTIV][DEBUG] Entering motivation_elicitation_node") 

    messages: List[Union[BaseMessage, dict]] = state.get('messages', []) # Type hint updated
    
    raw_topic: Optional[str] = state.get('raw_topic')
    raw_idea: Optional[str] = state.get('raw_idea')
    has_asked_initial: bool = state.get('has_asked_initial', False)
    
    print(f"[MOTIV][DEBUG] state.raw_topic={raw_topic}")
    print(f"[MOTIV][DEBUG] state.raw_idea={raw_idea}")
    print(f"[MOTIV][DEBUG] state.has_asked_initial={has_asked_initial}")
    print(f"[MOTIV][DEBUG] state.messages length={len(messages)}") 

    # 첫 사용자 입력으로 raw_topic/idea 설정 (기존 로직 유지)
    if not has_asked_initial and (not raw_topic or not raw_idea) and messages:
        first_human_msg_content = None
        # Handle both object and dict for first message extraction
        first_msg_data = messages[0]
        if isinstance(first_msg_data, HumanMessage):
            first_human_msg_content = first_msg_data.content
        elif isinstance(first_msg_data, dict) and first_msg_data.get("type") == "human":
            first_human_msg_content = first_msg_data.get("content")
            
        if first_human_msg_content:
            raw_topic = raw_topic or first_human_msg_content
            raw_idea  = raw_idea  or first_human_msg_content
            print(f"[MOTIV][DEBUG] Fallback: raw_topic/idea set from first message: {raw_idea}")

    llm = get_high_performance_llm()
    structured = llm.with_structured_output(MotivationClarityOutput)

    system_prompt = ( 
        # (기존 시스템 프롬프트 내용 유지)
        """
# 역할: 당신은 사용자의 동기 설명을 분석하고 명확성을 판단하는 AI 분석가이자 질문자입니다. 목표는 사용자가 자신의 핵심 동기('Why')를 충분히 깊고 명확하게 이해했는지 평가하고, 그렇지 않다면 더 깊은 성찰을 유도하는 추가 질문을 던지는 것입니다.

# 핵심 지침:
1.  **명확성 평가:** 사용자의 답변이 아이디어의 근본적인 'Why'(궁극적 목적, 핵심 가치, 해결하려는 진짜 문제 등)를 구체적이고 설득력 있게 설명하는지 평가하세요. 피상적이거나 모호한 답변은 '불명확'으로 판단합니다.
2.  **판단 기준:**
    * **명확 (Clear - is_motivation_clear=True):** 사용자가 자신의 핵심 동기를 구체적인 용어로 설명하고, 그것이 왜 중요한지에 대한 논리적인 이유를 제시하며, 아이디어와의 연결성이 분명합니다. 다음 단계(가정 탐색)로 넘어가도 좋습니다.
    * **불명확 (Unclear - is_motivation_clear=False):** 답변이 추상적이거나, 동문서답이거나, 여러 동기가 혼재되어 핵심을 파악하기 어렵거나, 논리적 근거가 부족합니다. 추가 질문이 필요합니다.
3.  **추가 질문 생성 (불명확 시):** 만약 동기가 불명확하다면, 사용자의 답변 내용 중 **가장 불명확하거나 더 깊이 탐색해야 할 부분**을 정확히 짚어내는 **단 하나의 구체적이고 통찰력 있는 후속 질문**을 생성하세요. 막연히 "더 자세히 설명해주세요"라고 하지 마세요. (예: "말씀하신 '성장'이 구체적으로 어떤 종류의 성장을 의미하는지 더 설명해주실 수 있나요?", "그 목표가 아이디어의 [특정 측면]과 어떻게 직접적으로 연결되는지 궁금합니다.")
4.  **동기 요약 생성 (명확 시):** 만약 동기가 명확하다면, 파악된 핵심 동기를 **다음 단계를 위해 간결하게 요약**하여 `summary_of_motivation` 필드에 담으세요.

# 구조화된 출력 형식: {"is_motivation_clear": boolean, "clarification_question": string | null, "summary_of_motivation": string | null}

# 출력 지침: 위 역할과 지침에 따라 사용자의 답변을 분석하여 명확성 여부를 판단하고, 필요한 경우 추가 질문을, 명확한 경우 동기 요약을 포함한 JSON 객체를 생성하세요.
        """.strip()
    )

    # --- 수정: messages 리스트 처리 시 dict 형태도 고려 ---
    if not has_asked_initial:
        print("[MOTIV][DEBUG] 첫 질문 분기 (user_prompt by raw_topic/raw_idea)")
        user_prompt = f"Topic: {raw_topic or 'N/A'}\nIdea: {raw_idea or 'N/A'}"
    else:
        print("[MOTIV][DEBUG] 후속 질문 분기 (user_prompt by messages)")
        history_lines = []
        print(f"  [MOTIV][DEBUG] Building history from messages list (length {len(messages)}): {messages}") # 상세 로깅 추가
        for i, msg_data in enumerate(messages): # messages 리스트 순회 (dict 또는 BaseMessage 객체 포함 가능)
            role = None
            content = None
            msg_type_str = None # 로그용 타입 문자열

            if isinstance(msg_data, HumanMessage):
                role = "User"
                content = msg_data.content
                msg_type_str = "HumanMessage object"
            elif isinstance(msg_data, AIMessage):
                role = "Assistant"
                content = msg_data.content
                msg_type_str = "AIMessage object"
            elif isinstance(msg_data, dict): # 직렬화된 dict 형태 처리
                msg_type_str = f"dict (type: {msg_data.get('type')})"
                if msg_data.get("type") == "human":
                    role = "User"
                    content = msg_data.get("content")
                elif msg_data.get("type") == "ai":
                    role = "Assistant"
                    content = msg_data.get("content")
            
            if role and content is not None:
                history_lines.append(f"- {role}: {content}")
                print(f"    [MOTIV][DEBUG] Added msg {i} ({msg_type_str}) to history_lines.")
            else:
                 print(f"    [MOTIV][WARN] Skipped msg {i} (type: {type(msg_data)}, content: {str(msg_data)[:100]}...) - Couldn't determine role/content.")

        
        if history_lines:
             user_prompt = "Dialogue History:\n" + "\n".join(history_lines)
        else:
             # 이 경우는 거의 없어야 함 (최소한 사용자 메시지는 있을 것이므로)
             user_prompt = "No dialogue history available in messages." 
             print("[MOTIV][WARN] No history lines generated from messages list.")
    # --- END 수정 ---
    print(f"[MOTIV][DEBUG] user_prompt={user_prompt!r}")

    try:
        print("[MOTIV][INFO] Calling LLM for motivation clarity...")
        resp: MotivationClarityOutput = await structured.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt) # 생성된 user_prompt 사용
        ])
        print(f"[MOTIV][DEBUG] LLM 응답(resp)={resp}")
        print("[MOTIV][INFO] LLM call completed.")

    except Exception as e:
        # (오류 처리 로직 유지)
        print(f"[MOTIV][ERROR] LLM 호출 실패: {e}")
        import traceback
        traceback.print_exc() 
        err_q = f"(시스템 오류: 동기 판단 중 문제가 발생했습니다. {e})"
        # 오류 발생 시에도 messages 리스트는 현재까지의 내용을 유지하며 반환
        return {
            "messages": messages + [AIMessage(content=err_q)], 
            "motivation_cleared": False,
            "clarification_question": err_q, 
            "has_asked_initial": True, 
            "assistant_message": err_q, 
            "error_message": f"LLM Error in motivation_elicitation: {e}" 
        }

    # 동기 불명확 → 후속 질문 상태 반환
    if not resp.is_motivation_clear:
        print("[MOTIV][DEBUG] 동기 불명확 → returning state with clarification_question")
        q = resp.clarification_question or "(후속 질문 생성 실패)"
        updated_messages = messages + [AIMessage(content=q)] # 현재 messages에 AI 응답 추가
        return_state = {
            "messages": updated_messages, 
            "motivation_cleared": False,
            "clarification_question": q, 
            "has_asked_initial": True,
            "assistant_message": q 
        }
        print(f"[MOTIV][DEBUG] Returning state: {return_state}")
        return return_state

    # 동기 명확 → 요약 포함 상태 반환 (다음 노드로 진행)
    print("[MOTIV][DEBUG] 동기 명확 → returning summary state")
    msg = resp.summary_of_motivation or "(요약 정보 없음)"
    updated_messages = messages + [AIMessage(content=msg)] # 현재 messages에 AI 응답 추가
    return_state = {
        "messages": updated_messages, 
        "motivation_cleared": True,
        "final_motivation_summary": msg, 
        "has_asked_initial": True, 
        "assistant_message": msg 
    }
    print(f"[MOTIV][DEBUG] Returning state: {return_state}")
    return return_state
