# backend/app/graph_nodes/why/identify_assumptions_node.py

from typing import Dict, Any, List, Union
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
# from langgraph.types import interrupt # Interrupt 사용 안 함
from pydantic import BaseModel, Field

from ...core.llm_provider import get_high_performance_llm
from ...models.why_graph_state import WhyGraphState

class IdentifiedAssumptionsOutput(BaseModel):
    identified_assumptions: List[str] = Field(
        ...,
        description=(
            "아이디어와 동기를 바탕으로 식별된 핵심적인 기저 가정들의 목록입니다. "
            "가장 치명적이거나 성공에 중요도가 높은 순서로 정렬되어야 합니다."
        )
    )

async def identify_assumptions_node(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Identify Assumptions 노드:
    아이디어 요약과 동기 요약을 기반으로 핵심 가정을 3~5개 식별하고 중요도 순으로 정렬하여
    상태를 업데이트하고 다음 노드로 진행합니다. (사용자에게 직접 메시지 전달 안 함)
    """
    print("[IDENT][DEBUG] Entering identify_assumptions_node")

    messages: List[Union[BaseMessage, dict]] = state.get('messages', [])
    
    # --- messages 리스트 처리 로직 (motivation_elicitation_node와 동일) ---
    processed_messages_for_prompt = []
    history_lines_for_prompt = []
    print(f"  [IDENT][DEBUG] Building history from messages list (length {len(messages)}): {messages}")
    for i, msg_data in enumerate(messages): 
        role = None
        content = None
        msg_obj = None 

        if isinstance(msg_data, HumanMessage):
            role = "User"
            content = msg_data.content
            msg_obj = msg_data
        elif isinstance(msg_data, AIMessage):
            role = "Assistant"
            content = msg_data.content
            msg_obj = msg_data
        elif isinstance(msg_data, dict): 
            if msg_data.get("type") == "human":
                role = "User"
                content = msg_data.get("content")
                msg_obj = HumanMessage(content=content, additional_kwargs=msg_data.get("additional_kwargs", {})) 
            elif msg_data.get("type") == "ai":
                role = "Assistant"
                content = msg_data.get("content")
                msg_obj = AIMessage(content=content, additional_kwargs=msg_data.get("additional_kwargs", {})) 
        
        if role and content is not None:
            history_lines_for_prompt.append(f"- {role}: {content}")
            if msg_obj: 
                 processed_messages_for_prompt.append(msg_obj)
            print(f"    [IDENT][DEBUG] Processed msg {i} for prompt.")
        else:
             print(f"    [IDENT][WARN] Skipped msg {i} (type: {type(msg_data)})")
    # --------------------------------------------------------------------

    idea_summary = state.get('idea_summary')
    motivation_summary = state.get('motivation_summary') or state.get('final_motivation_summary') # motivation_summary 우선 사용
    
    if not idea_summary or not motivation_summary:
        missing = []
        if not idea_summary: missing.append('idea_summary')
        if not motivation_summary: missing.append('motivation_summary/final_motivation_summary')
        error_msg = f"IdentifyAssumptions: Missing required state fields: {', '.join(missing)}"
        print(f"[IDENT][ERROR] {error_msg}")
        # 오류 발생 시에도 messages는 유지하며 반환
        return {"error_message": error_msg, "messages": processed_messages_for_prompt} 

    llm = get_high_performance_llm()
    structured_llm = llm.with_structured_output(IdentifiedAssumptionsOutput)

    system_prompt = f"""
# 역할: 당신은 사용자의 아이디어와 그 동기 이면에 숨어있는 **핵심적인 기저 가정(underlying assumptions)**을 식별하고 **그 중요도를 평가**하는 날카로운 분석가입니다. 당신의 목표는 명시적으로 언급되지 않았더라도 아이디어가 성공하거나 동기가 타당하기 위해 **암묵적으로 전제하고 있는 조건, 믿음, 또는 인과관계**를 찾아내고, **가장 중요하거나 아이디어에 치명적인 영향을 미치는 순서대로 정렬**하여 목록으로 반환하는 것입니다.

# 입력 정보:
* **아이디어 요약:** {idea_summary}
* **동기 요약:** {motivation_summary}
* **대화 내용:** 아래 대화 내용을 참고하세요.
# 핵심 지침:
1. **심층 분석 및 가정 식별:** 아이디어 요약, 동기 요약, 그리고 전체 대화 내용을 면밀히 분석하여 숨겨진 핵심 전제 3~5개를 식별하세요.
2. **중요도 평가:** 각 가정이 틀렸을 때 아이디어에 미치는 **치명적 영향**을 기준으로 평가하세요.
3. **정렬:** 중요한 가정이 리스트 상단에 오도록 내림차순으로 정렬하세요.
4. **명확하고 독립적 문장:** 각 가정을 간결하고 독립된 문장으로 작성하세요.
5. **구조화된 출력:** 지정된 JSON 형식({{"identified_assumptions": ["가정1", "가정2", ...]}})으로 출력하세요.
"""
    # Use the full dialogue history for context
    user_prompt = (
        f"Idea Summary: {idea_summary}\n"
        f"Motivation Summary: {motivation_summary}\n\n"
        "Dialogue History:\n" + "\n".join(history_lines_for_prompt) 
    )

    print(f"[IDENT][DEBUG] user_prompt for identification: {user_prompt}")

    try:
        print("[IDENT][INFO] Calling LLM for assumption identification...")
        output: IdentifiedAssumptionsOutput = await structured_llm.ainvoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ])
        assumptions = output.identified_assumptions
        print("[IDENT][INFO] LLM call completed.")
        print(f"[IDENT][DEBUG] Identified assumptions: {assumptions}")
    except Exception as e:
        print(f"[IDENT][ERROR] LLM call failed: {e}")
        import traceback
        traceback.print_exc()
        error_msg = f"(System Error: Failed to identify assumptions - {e})"
        # Return error state, keeping existing messages
        return {"error_message": error_msg, "messages": processed_messages_for_prompt}

    # --- Return state dictionary without Interrupt ---
    # This node updates the state and lets the graph proceed.
    # No direct message to the user at this point.
    return_state = {
        'messages': processed_messages_for_prompt, # Keep the processed messages
        'identified_assumptions': assumptions,
        'probed_assumptions': [], # Reset probed assumptions list
        'assumptions_fully_probed': False, # Reset flag
        # Clear any potential question keys from previous steps if needed
        'clarification_question': None, 
        'assumption_question': None,
    }
    print(f"[IDENT][DEBUG] Returning state: {return_state}")
    return return_state
    # ---------------------------------------------
