# backend/app/core/why_orchestration.py

from typing import List, Optional, Dict, Any, Union
from fastapi import HTTPException
from langgraph.graph import StateGraph
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage 
from langchain_core.runnables import RunnableConfig
from langgraph.errors import Interrupt, GraphInterrupt # Interrupt는 이제 사용 안 함
from langgraph.checkpoint.memory import MemorySaver 
import copy

# (다른 import 유지)
from app.core.user_state import UserStateStore
from app.db.session import async_session_factory
from app.core.config import get_settings
from app.models.why_graph_state import WhyGraphState 
from app.graph_nodes.why.motivation_elicitation_node import motivation_elicitation_node
# 다른 노드들도 messages 채널을 사용하고 상태 딕셔너리를 반환하도록 수정 필요
from app.graph_nodes.why.summarize_idea_motivation_node import summarize_idea_motivation_node
# identify_assumptions_node 와 probe_assumption_node도 Interrupt 대신 dict를 반환하도록 수정 필요
from app.graph_nodes.why.identify_assumptions_node import identify_assumptions_node 
from app.graph_nodes.why.probe_assumption_node import probe_assumption_node 
from app.graph_nodes.why.findings_summarization_node import findings_summarization_node 
from app.graph_nodes.why.free_conversation_node import free_conversation_node 


settings = get_settings()
checkpointer = MemorySaver() # MemorySaver 사용 유지
user_store   = UserStateStore(async_session_factory) 

workflow = StateGraph(WhyGraphState)
# --- 노드 및 엣지 정의 (기존과 동일) ---
workflow.add_node("motivation_elicitation", motivation_elicitation_node)
workflow.add_node("summarize_idea_motivation", summarize_idea_motivation_node)
workflow.add_node("identify_assumptions", identify_assumptions_node)
workflow.add_node("probe_assumption", probe_assumption_node)
workflow.add_node("findings_summarization", findings_summarization_node)
workflow.add_node("free_conversation", free_conversation_node)
workflow.set_entry_point("motivation_elicitation")

# 조건부 엣지는 상태의 필드를 기반으로 하므로 그대로 유지 가능
workflow.add_conditional_edges("motivation_elicitation", {
    "motivation_elicitation": lambda st: not st.get("motivation_cleared", False),
    "summarize_idea_motivation": lambda st:     st.get("motivation_cleared", False),
})
# (다른 엣지 정의 유지)
workflow.add_conditional_edges("summarize_idea_motivation", {
    "identify_assumptions": lambda st: bool(st.get("idea_summary")) and bool(st.get("motivation_summary"))
})
workflow.add_conditional_edges("identify_assumptions", {
    "probe_assumption": lambda st: len(st.get("identified_assumptions", [])) > 0,
    "findings_summarization": lambda st: len(st.get("identified_assumptions", [])) == 0, 
})
workflow.add_conditional_edges("probe_assumption", {
    # probe_assumption 노드가 사용자 입력을 기다리는 상태인지 확인하는 키 추가 필요 (예: 'needs_probe_input': True)
    # 또는 마지막 메시지가 AI 질문인지 확인하는 방식으로 처리 가능
    "probe_assumption": lambda st: len(set(st.get("probed_assumptions", []))) < len(st.get("identified_assumptions", [])) and not st.get("assumptions_fully_probed"), # assumptions_fully_probed 플래그 사용
    "findings_summarization": lambda st: len(set(st.get("probed_assumptions", []))) >= len(st.get("identified_assumptions", [])) or st.get("assumptions_fully_probed"), # 모든 가정이 탐색되었으면 요약으로
})
workflow.add_conditional_edges("findings_summarization", {
    "free_conversation": lambda st: bool(st.get("findings_summary"))
})
workflow.add_edge("free_conversation", "free_conversation") 
# --- END 노드 및 엣지 정의 ---

app_why_graph = workflow.compile(checkpointer=checkpointer) 

def _serialize_state_for_db(state: Dict[str, Any]) -> Dict[str, Any]:
    # (기존 함수 내용 유지 - messages 직렬화 포함)
    if not state: return {}
    serializable_state = copy.deepcopy(state) 
    if 'messages' in serializable_state and isinstance(serializable_state['messages'], list):
        serializable_state['messages'] = [
            {"type": msg.type, "content": msg.content, "additional_kwargs": msg.additional_kwargs if hasattr(msg, 'additional_kwargs') else {}} if isinstance(msg, BaseMessage) else msg
            for msg in serializable_state['messages']
        ]
    if 'channel_values' in serializable_state and isinstance(serializable_state['channel_values'], dict):
        for channel, msgs_list in serializable_state['channel_values'].items():
            if isinstance(msgs_list, list):
                serializable_state['channel_values'][channel] = [
                    {"type": msg.type, "content": msg.content, "additional_kwargs": msg.additional_kwargs if hasattr(msg, 'additional_kwargs') else {}} if isinstance(msg, BaseMessage) else msg
                    for msg in msgs_list
                ]
    return serializable_state

async def run_why_exploration_turn(
    session_id: str,
    user_input: Optional[str] = None,
    initial_topic: Optional[str] = None 
) -> Optional[str]:
    state = await user_store.load(session_id) or {} 
    print(f"[DEBUG Orchestrator] Loaded state from UserStore for session {session_id}: {str(state)[:500]}...")

    is_new_session = not state
    if is_new_session: 
        print(f"[DEBUG Orchestrator] Session {session_id} is new or state is empty, initializing.")
        # (상태 초기화 로직 유지)
        state = {
            "messages": [], "channel_values": {"__default__": []}, "dialogue_history": [], 
            "raw_topic": initial_topic, "raw_idea": None, "has_asked_initial": False,
            "motivation_cleared": False, "final_motivation_summary": "", "idea_summary": "",
            "motivation_summary": "", "identified_assumptions": [], "probed_assumptions": [], 
            "assumptions_fully_probed": False, "findings_summary": "", "older_history_summary": "",
            "error_message": None, "metadata": {}, "versions_seen": {}, 
        }

    if user_input:
        print(f"[DEBUG Orchestrator] User input for session {session_id}: {user_input}")
        # (사용자 입력 처리 로직 유지 - messages 채널 사용)
        user_h_message = HumanMessage(content=user_input)
        if not isinstance(state.get("messages"), list): state["messages"] = []
        state["messages"].append(user_h_message)
        if not isinstance(state.get("channel_values"), dict): state["channel_values"] = {"__default__": []}
        state.setdefault("channel_values", {}).setdefault("__default__", []).append(user_h_message)
        if not state.get('raw_idea') and not state.get('has_asked_initial'): 
            state['raw_idea'] = user_input
            if not state.get('raw_topic') and is_new_session: 
                 state['raw_topic'] = user_input
    
    print(f"[DEBUG Orchestrator] State BEFORE UserStore save (if any) and BEFORE ainvoke for session {session_id}:")
    # (상세 로깅 유지)
    print(f"  - messages: {str(state.get('messages'))[:300]}...")
    print(f"  - has_asked_initial: {state.get('has_asked_initial')}")

    graph_input = state.copy() 
    print(f"[DEBUG Orchestrator] graph_input (before ainvoke) for session {session_id}: {str(graph_input)[:500]}...")

    try:
        run_config: RunnableConfig = {"configurable": {"thread_id": session_id}} 
        print(f"[DEBUG Orchestrator] Calling app_why_graph.ainvoke for session {session_id} with MemorySaver...")
        
        final_state_after_ainvoke = await app_why_graph.ainvoke(graph_input, run_config)
        
        print(f"[DEBUG Orchestrator] app_why_graph.ainvoke finished for session {session_id}.")
        if isinstance(final_state_after_ainvoke, dict):
            print(f"  Keys in final_state_after_ainvoke: {list(final_state_after_ainvoke.keys())}")
            print(f"  final_state_after_ainvoke['messages'] sample: {str(final_state_after_ainvoke.get('messages'))[:400]}...")
            print(f"  final_state_after_ainvoke['has_asked_initial']: {final_state_after_ainvoke.get('has_asked_initial')}")
            print(f"  final_state_after_ainvoke['motivation_cleared']: {final_state_after_ainvoke.get('motivation_cleared')}") 
            # 다른 중요한 상태 필드 로깅 추가 (예: identify/probe 관련)
            print(f"  final_state_after_ainvoke['identified_assumptions']: {final_state_after_ainvoke.get('identified_assumptions')}")
            print(f"  final_state_after_ainvoke['probed_assumptions']: {final_state_after_ainvoke.get('probed_assumptions')}")
            print(f"  final_state_after_ainvoke['assumptions_fully_probed']: {final_state_after_ainvoke.get('assumptions_fully_probed')}")

        else:
            print(f"  final_state_after_ainvoke is not a dict: {type(final_state_after_ainvoke)}")

        assistant_response_to_user = None
        state_to_save_in_user_store = final_state_after_ainvoke.copy() if isinstance(final_state_after_ainvoke, dict) else {}

        # --- 수정된 응답 결정 로직 ---
        if isinstance(final_state_after_ainvoke, dict):
            messages_list = final_state_after_ainvoke.get('messages', [])
            last_message_obj = messages_list[-1] if messages_list else None

            # 1. 마지막 메시지가 AI 메시지인지 확인
            if isinstance(last_message_obj, AIMessage):
                # 2. 이 AI 메시지가 사용자 입력을 요구하는 질문인지 판단
                #    (motivation_cleared=False 또는 assumptions_fully_probed=False 등 상태 확인)
                motivation_cleared = final_state_after_ainvoke.get('motivation_cleared', False)
                assumptions_fully_probed = final_state_after_ainvoke.get('assumptions_fully_probed', False)
                # 가정 식별 단계 메시지인지 확인 (identify_assumptions_node가 메시지 추가 시) - 예시
                # is_assumption_id_msg = "다음은 식별된 핵심 가정들입니다" in last_message_obj.content 

                if not motivation_cleared:
                     assistant_response_to_user = last_message_obj.content
                     print(f"[DEBUG Orchestrator] Motivation not cleared. Returning question: {assistant_response_to_user}")
                elif final_state_after_ainvoke.get('identified_assumptions') and not assumptions_fully_probed:
                     # 동기는 명확해졌고, 가정이 식별되었으나 아직 전부 탐색되지 않음 -> 가정 탐색 질문일 가능성 높음
                     assistant_response_to_user = last_message_obj.content
                     print(f"[DEBUG Orchestrator] Assumptions identified but not fully probed. Returning question: {assistant_response_to_user}")
                # (Free conversation 등 다른 사용자 입력 대기 상태 추가 가능)
                else:
                     # 동기 명확, 가정 탐색 완료 등 -> 최종 요약 또는 다른 완료 메시지일 수 있음
                     assistant_response_to_user = last_message_obj.content
                     print(f"[DEBUG Orchestrator] Graph likely finished or in free conversation. Returning last AI message: {assistant_response_to_user}")

            # 3. 마지막 메시지가 AI 메시지가 아니거나, AI 메시지지만 질문이 아닌 경우 (예: summarize 노드 직후)
            else:
                 print(f"[DEBUG Orchestrator] Last message is not AI or not considered a question requiring user input.")
                 # 이 경우, 다음 턴을 기다릴 필요 없이 흐름이 완료되었거나 내부적으로 계속 진행되어야 함
                 # 하지만 현재 구조에서는 ainvoke가 멈췄으므로, 사용자에게 반환할 메시지가 없을 수 있음
                 assistant_response_to_user = "(흐름 진행 중...)" # 또는 None이나 다른 적절한 메시지

        else: # final_state_after_ainvoke가 dict가 아닌 경우
            print("[WARN Orchestrator] final_state_after_ainvoke is not a dict. Cannot determine response.")
            assistant_response_to_user = "(오류: 상태 처리 불가)"
        # --- END 수정된 응답 결정 로직 ---


        # UserStore에 최종 상태 저장
        try:
            if isinstance(state_to_save_in_user_store, dict) and state_to_save_in_user_store:
                # 저장 전에 dialogue_history 재구성 (messages 기반)
                final_messages = state_to_save_in_user_store.get("messages", [])
                state_to_save_in_user_store["dialogue_history"] = [
                    {"role": "user" if isinstance(m, HumanMessage) else "assistant", "content": m.content}
                    for m in final_messages if isinstance(m, (HumanMessage, AIMessage))
                ]
                print(f"  Reconstructed dialogue_history before saving.")

                print(f"[DEBUG Orchestrator] State TO BE SAVED to UserStore for session {session_id}:")
                # (상세 로깅 유지)
                print(f"  - messages: {str(state_to_save_in_user_store.get('messages'))[:300]}...")
                print(f"  - dialogue_history: {str(state_to_save_in_user_store.get('dialogue_history'))[:300]}...")
                print(f"  - has_asked_initial: {state_to_save_in_user_store.get('has_asked_initial')}")
                print(f"  - motivation_cleared: {state_to_save_in_user_store.get('motivation_cleared')}")
                print(f"  - assumptions_fully_probed: {state_to_save_in_user_store.get('assumptions_fully_probed')}")

                serializable_state = _serialize_state_for_db(state_to_save_in_user_store)
                await user_store.upsert(session_id, serializable_state)
                print(f"[DEBUG Orchestrator] ✓ State saved to UserStore for session {session_id}.")
            # (기존 empty state 경고 로그 유지)

        except Exception as e_upsert:
            # (기존 예외 처리 로직 유지)
            print(f"[ERROR Orchestrator] Failed to upsert state to UserStore for session {session_id}: {e_upsert}")
            if assistant_response_to_user: return assistant_response_to_user
            raise HTTPException(status_code=500, detail=f"Error saving application state: {e_upsert}")

        return assistant_response_to_user # 결정된 응답 반환

    except GraphInterrupt as gi: 
        # (기존 예외 처리 로직 유지)
        print(f"[ERROR Orchestrator] Unexpected GraphInterrupt exception caught for session {session_id}: {gi.value}")
        try:
            current_state_serializable = _serialize_state_for_db(state) 
            await user_store.upsert(session_id, current_state_serializable)
        except Exception as e_gi_save:
            print(f"  Failed to save pre-ainvoke state on GraphInterrupt for session {session_id}: {e_gi_save}")
        return str(gi.value) 

    except Exception as e:
        # (기존 예외 처리 로직 유지)
        print(f"[ERROR Orchestrator] Unhandled exception in orchestration for session {session_id}: {e}")
        import traceback
        traceback.print_exc()
        if "LogStreamCallbackHandler" in str(e): 
             print("  [WARN Orchestrator] Ignoring LogStreamCallbackHandler error.")
             if not isinstance(e, HTTPException): raise HTTPException(status_code=500, detail=f"Internal error during callback: {e}")
             else: raise
        elif not isinstance(e, HTTPException): raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
        else: raise
